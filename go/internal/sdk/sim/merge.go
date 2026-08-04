package sim

import (
	"bufio"
	"encoding/json"
	"io"
	"os"
	"sort"
)

// MergeShards concatenates per-worker output into one artifact set per mode.
//
// Shards cover contiguous, ascending id ranges, so concatenating them in worker
// order yields an id-ordered pool -- which matters because the published files
// are sha256'd into config.json and a reshuffled pool would change every hash
// with no math change.
//
// The books files are joined BYTE-WISE. That is valid: a .zst stream may contain
// multiple frames back to back, and every conforming decoder reads them as one
// continuous stream.
func MergeShards(l *Layout, mode string, shards []string) error {
	if err := concatFiles(l.booksPath(mode), pathsFor(l.booksPath, shards)); err != nil {
		return err
	}
	if err := concatFiles(l.lutPath(mode), pathsFor(l.lutPath, shards)); err != nil {
		return err
	}
	if err := concatFiles(l.segmentedPath(mode), pathsFor(l.segmentedPath, shards)); err != nil {
		return err
	}
	if err := mergeForceRecords(l.forcePath(mode), pathsFor(l.forcePath, shards)); err != nil {
		return err
	}

	// Remove the shards only after every merge has succeeded, so a failure leaves
	// the raw output recoverable rather than destroying a long run.
	for _, s := range shards {
		os.Remove(l.booksPath(s))
		os.Remove(l.lutPath(s))
		os.Remove(l.segmentedPath(s))
		os.Remove(l.forcePath(s))
	}
	return nil
}

func pathsFor(f func(string) string, shards []string) []string {
	out := make([]string, len(shards))
	for i, s := range shards {
		out[i] = f(s)
	}
	return out
}

func concatFiles(dst string, srcs []string) error {
	out, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer out.Close()
	w := bufio.NewWriterSize(out, 1<<20)

	for _, src := range srcs {
		in, err := os.Open(src)
		if err != nil {
			return err
		}
		_, err = io.Copy(w, bufio.NewReaderSize(in, 1<<20))
		in.Close()
		if err != nil {
			return err
		}
	}
	return w.Flush()
}

// mergeForceRecords unions the per-shard force maps.
//
// The same event description turns up in several shards, so records are keyed by
// their search terms and their book id lists concatenated. Ids are then sorted so
// the file is deterministic regardless of which worker finished first -- the
// optimizer does not care about order, but a reproducible artifact does.
func mergeForceRecords(dst string, srcs []string) error {
	type key = string
	merged := map[key]*forceRecord{}

	for _, src := range srcs {
		f, err := os.Open(src)
		if err != nil {
			return err
		}
		var records []forceRecord
		err = json.NewDecoder(bufio.NewReaderSize(f, 1<<20)).Decode(&records)
		f.Close()
		if err != nil {
			return err
		}
		for i := range records {
			r := &records[i]
			k, err := searchKey(r.Search)
			if err != nil {
				return err
			}
			if existing, ok := merged[k]; ok {
				existing.BookIDs = append(existing.BookIDs, r.BookIDs...)
				existing.TimesTriggered += r.TimesTriggered
			} else {
				cp := *r
				merged[k] = &cp
			}
		}
	}

	out := make([]forceRecord, 0, len(merged))
	keys := make([]string, 0, len(merged))
	for k := range merged {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		r := merged[k]
		sort.Ints(r.BookIDs)
		out = append(out, *r)
	}

	f, err := os.Create(dst)
	if err != nil {
		return err
	}
	defer f.Close()
	w := bufio.NewWriterSize(f, 1<<20)
	if err := json.NewEncoder(w).Encode(out); err != nil {
		return err
	}
	return w.Flush()
}

func searchKey(terms []forceTerm) (string, error) {
	b, err := json.Marshal(terms)
	return string(b), err
}
