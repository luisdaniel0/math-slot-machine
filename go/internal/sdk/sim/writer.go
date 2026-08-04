// Package sim drives simulation runs and writes the published artifacts.
package sim

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"strconv"

	"github.com/klauspost/compress/zstd"

	"starwake/internal/sdk/engine"
)

// Layout mirrors the Python library/ tree so the Rust optimizer and the
// publishing path can consume Go's output unchanged -- but ROOTED SOMEWHERE ELSE.
//
// ⚠ NOTHING HERE MAY WRITE INTO games/<game>/library/. That tree holds the
// converged production pool (~11 GB, gitignored, protected by no branch), and the
// Python sweep harnesses already demonstrate how easily a tool that reuses the
// standard paths destroys it.
type Layout struct{ Root string }

// NewLayout prepares the output directories under root.
func NewLayout(root string) (*Layout, error) {
	for _, d := range []string{"publish_files", "lookup_tables", "forces"} {
		if err := os.MkdirAll(filepath.Join(root, d), 0o755); err != nil {
			return nil, err
		}
	}
	return &Layout{Root: root}, nil
}

func (l *Layout) booksPath(mode string) string {
	return filepath.Join(l.Root, "publish_files", "books_"+mode+".jsonl.zst")
}
func (l *Layout) lutPath(mode string) string {
	return filepath.Join(l.Root, "lookup_tables", "lookUpTable_"+mode+".csv")
}
func (l *Layout) segmentedPath(mode string) string {
	return filepath.Join(l.Root, "lookup_tables", "lookUpTableSegmented_"+mode+".csv")
}
func (l *Layout) forcePath(mode string) string {
	return filepath.Join(l.Root, "forces", "force_record_"+mode+".json")
}

// bookJSON is the published book shape.
//
// ⚠ id, events and payoutMultiplier are REQUIRED by the RGS
// (docs/rgs_docs/data_format.md), and payoutMultiplier must exactly match the
// third column of this mode's lookup table -- Stake extracts and hashes both to
// confirm they agree.
type bookJSON struct {
	ID               int            `json:"id"`
	PayoutMultiplier int64          `json:"payoutMultiplier"`
	Events           []engine.Event `json:"events"`
	Criteria         string         `json:"criteria"`
	BaseGameWins     float64        `json:"baseGameWins"`
	FreeGameWins     float64        `json:"freeGameWins"`
}

// Writer streams one mode's artifacts to disk.
//
// Streaming, not buffered-in-memory: Python holds every book of a batch in RAM
// and that is what took the WSL VM down mid-buy_corvus (~15 GB live across 14
// forked workers). Writing each book as it completes keeps the resident set flat
// regardless of sim count, which also removes the batching_size tuning trap.
type Writer struct {
	mode string

	booksFile *os.File
	zw        *zstd.Encoder
	books     *bufio.Writer
	enc       *json.Encoder

	lut     *os.File
	lutBuf  *bufio.Writer
	seg     *os.File
	segBuf  *bufio.Writer
	layout  *Layout
	closed  bool
	written int

	// Force keys seen anywhere in this mode, and which books produced them.
	forces map[engine.ForceKey][]int
}

// NewWriter opens a mode's output files.
func NewWriter(l *Layout, mode string) (*Writer, error) {
	w := &Writer{mode: mode, layout: l, forces: make(map[engine.ForceKey][]int)}

	var err error
	if w.booksFile, err = os.Create(l.booksPath(mode)); err != nil {
		return nil, err
	}
	// A large window pays off here: books repeat their event vocabulary heavily,
	// so zstd finds a great deal of cross-book redundancy.
	w.zw, err = zstd.NewWriter(w.booksFile,
		zstd.WithEncoderLevel(zstd.SpeedDefault),
		zstd.WithWindowSize(1<<22))
	if err != nil {
		return nil, err
	}
	w.books = bufio.NewWriterSize(w.zw, 1<<20)
	w.enc = json.NewEncoder(w.books)

	if w.lut, err = os.Create(l.lutPath(mode)); err != nil {
		return nil, err
	}
	w.lutBuf = bufio.NewWriterSize(w.lut, 1<<20)

	if w.seg, err = os.Create(l.segmentedPath(mode)); err != nil {
		return nil, err
	}
	w.segBuf = bufio.NewWriterSize(w.seg, 1<<20)

	return w, nil
}

// Write emits one completed book.
//
// ids are 0-BASED, matching Python. (The `library` dict is keyed by sim+1, but
// make_lookup_tables writes library[sim]["id"], which is the book's own id field
// = the simulation number. Both the LUT and the force record use that, so the
// published ids run 0..N-1.)
func (w *Writer) Write(id int, b *engine.Book, forced []engine.ForceKey, cap float64) error {
	payout := payoutCents(b.PayoutMultiplier, cap)

	if err := w.enc.Encode(&bookJSON{
		ID:               id,
		PayoutMultiplier: payout,
		Events:           b.Events,
		Criteria:         b.Criteria,
		BaseGameWins:     b.BasegameWins,
		FreeGameWins:     b.FreegameWins,
	}); err != nil {
		return err
	}

	// LUT: id, weight, payout. Weight is 1 pre-optimizer -- the Rust optimizer
	// rewrites these into the published lookUpTable_<mode>_0.csv.
	w.lutBuf.WriteString(strconv.Itoa(id))
	w.lutBuf.WriteString(",1,")
	w.lutBuf.WriteString(strconv.FormatInt(payout, 10))
	w.lutBuf.WriteByte('\n')

	// Segmented LUT: id, criteria, basegame, freegame. Joined to the optimized
	// LUT for per-criteria splits.
	w.segBuf.WriteString(strconv.Itoa(id))
	w.segBuf.WriteByte(',')
	w.segBuf.WriteString(b.Criteria)
	w.segBuf.WriteByte(',')
	w.segBuf.WriteString(strconv.FormatFloat(b.BasegameWins, 'f', 2, 64))
	w.segBuf.WriteByte(',')
	w.segBuf.WriteString(strconv.FormatFloat(b.FreegameWins, 'f', 2, 64))
	w.segBuf.WriteByte('\n')

	// DEDUPE PER BOOK. A book usually produces the same description several times
	// (the same kind/symbol/mult on more than one payline, or on several feature
	// spins), and Python records a book id ONCE per description -- imprint_wins
	// guards with `book_id not in recorded_events[description]["bookIds"]`.
	// Appending every occurrence would inflate both timesTriggered and the id
	// list, which is exactly the weight denominator the optimizer fences on.
	//
	// Linear scan over the tail rather than a set: a book yields a handful of
	// distinct descriptions, so this is cheaper than allocating a map per book.
	seen := forced[:0:0]
	for _, f := range forced {
		dup := false
		for _, s := range seen {
			if s == f {
				dup = true
				break
			}
		}
		if dup {
			continue
		}
		seen = append(seen, f)
		w.forces[f] = append(w.forces[f], id)
	}

	w.written++
	return nil
}

// payoutCents converts a payout multiplier to integer hundredths.
//
// The clamp is applied to the TOTAL, which is what makes the published ceiling
// honest by construction: no book can report above its mode's max win.
func payoutCents(v, cap float64) int64 {
	if v > cap {
		v = cap
	}
	return int64(v*100 + 0.5)
}

// forceRecord is one searchable event description plus the books containing it.
type forceRecord struct {
	Search         []forceTerm `json:"search"`
	TimesTriggered int         `json:"timesTriggered"`
	BookIDs        []int       `json:"bookIds"`
}

type forceTerm struct {
	Name  string `json:"name"`
	Value string `json:"value"`
}

// Close flushes everything and writes the force record.
//
// Idempotent: callers defer Close for the error path and also call it explicitly
// to surface a flush failure, so a second call must be a no-op rather than an
// error on an already-closed file.
func (w *Writer) Close() error {
	if w.closed {
		return nil
	}
	w.closed = true
	if err := w.books.Flush(); err != nil {
		return err
	}
	if err := w.zw.Close(); err != nil {
		return err
	}
	if err := w.booksFile.Close(); err != nil {
		return err
	}
	if err := w.lutBuf.Flush(); err != nil {
		return err
	}
	if err := w.lut.Close(); err != nil {
		return err
	}
	if err := w.segBuf.Flush(); err != nil {
		return err
	}
	if err := w.seg.Close(); err != nil {
		return err
	}
	return w.writeForceRecord()
}

// writeForceRecord emits the file the Rust optimizer searches to build fences.
func (w *Writer) writeForceRecord() error {
	f, err := os.Create(w.layout.forcePath(w.mode))
	if err != nil {
		return err
	}
	defer f.Close()

	buf := bufio.NewWriterSize(f, 1<<20)
	records := make([]forceRecord, 0, len(w.forces))
	for key, ids := range w.forces {
		terms := []forceTerm{
			{Name: "gametype", Value: key.GameType},
			{Name: "kind", Value: strconv.Itoa(key.Kind)},
			{Name: "symbol", Value: key.Symbol},
		}
		if key.Mult != 0 {
			terms = append(terms, forceTerm{Name: "mult", Value: strconv.Itoa(key.Mult)})
		}
		records = append(records, forceRecord{
			Search: terms, TimesTriggered: len(ids), BookIDs: ids,
		})
	}
	if err := json.NewEncoder(buf).Encode(records); err != nil {
		return err
	}
	if err := buf.Flush(); err != nil {
		return err
	}
	return nil
}

// Count is the number of books written.
func (w *Writer) Count() int { return w.written }

var _ = fmt.Sprintf
