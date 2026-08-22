import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

export function useColumnOrder(reportKey: string, defaultColumns: string[]) {
  const [columns, setColumns] = useState<string[]>(defaultColumns);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    api
      .get(`/user-preferences/report_columns_${reportKey}`)
      .then((res) => {
        const saved = res.data.value;
        if (Array.isArray(saved) && saved.length > 0) {
          // Merge: keep saved order but add any new columns at end
          const merged = [
            ...saved.filter((c: string) => defaultColumns.includes(c)),
            ...defaultColumns.filter((c) => !saved.includes(c)),
          ];
          setColumns(merged);
        }
      })
      .catch(() => {}) // silently fall back to default
      .finally(() => setLoaded(true));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportKey]);

  const reorder = useCallback(
    (newOrder: string[]) => {
      setColumns(newOrder);
      api
        .put(`/user-preferences/report_columns_${reportKey}`, { value: newOrder })
        .catch(() => {}); // fire and forget
    },
    [reportKey],
  );

  return { columns, reorder, loaded };
}
