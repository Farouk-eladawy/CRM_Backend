import { useState, useEffect, useCallback } from 'react';
import api from '@/lib/api';

export function useColumnPreferences(
  reportKey: string,
  defaultColumns: string[],
) {
  const [columns, setColumns] = useState<string[]>(defaultColumns);
  const [visibility, setVisibilityState] = useState<Record<string, boolean>>(() => {
    const init: Record<string, boolean> = {};
    defaultColumns.forEach((c) => { init[c] = true; });
    return init;
  });
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Promise.all([
      api.get(`/user-preferences/report_columns_${reportKey}`).catch(() => ({ data: { value: null } })),
      api.get(`/user-preferences/report_columns_visible_${reportKey}`).catch(() => ({ data: { value: null } })),
    ]).then(([orderRes, visRes]) => {
      const savedOrder = orderRes.data?.value;
      if (Array.isArray(savedOrder) && savedOrder.length > 0) {
        const merged = [
          ...savedOrder.filter((c: string) => defaultColumns.includes(c)),
          ...defaultColumns.filter((c) => !savedOrder.includes(c)),
        ];
        setColumns(merged);
      }

      const savedVis = visRes.data?.value;
      const newVis: Record<string, boolean> = {};
      defaultColumns.forEach((c) => {
        newVis[c] = savedVis && typeof savedVis === 'object' ? savedVis[c] !== false : true;
      });
      setVisibilityState(newVis);
    }).finally(() => setLoaded(true));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reportKey]);

  const reorder = useCallback(
    (newOrder: string[]) => {
      setColumns(newOrder);
      api
        .put(`/user-preferences/report_columns_${reportKey}`, { value: newOrder })
        .catch(() => {});
    },
    [reportKey],
  );

  const saveVisibility = useCallback(
    (vis: Record<string, boolean>) => {
      setVisibilityState(vis);
      api
        .put(`/user-preferences/report_columns_visible_${reportKey}`, { value: vis })
        .catch(() => {});
    },
    [reportKey],
  );

  return { columns, reorder, loaded, visibility, saveVisibility };
}
