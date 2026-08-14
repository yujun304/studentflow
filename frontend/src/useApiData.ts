import { useEffect, useState } from "react";

import { api } from "./api";

export function useApiData<T>(path: string, initialValue: T, enabled = true) {
  const [data, setData] = useState(initialValue);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    let cancelled = false;
    setIsLoading(true);
    api<T>(path)
      .then((value) => {
        if (!cancelled) setData(value);
      })
      .catch((value) => {
        if (!cancelled) setError(value instanceof Error ? value : new Error("데이터를 불러오지 못했습니다."));
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, path]);

  return { data, isLoading, error };
}
