"use client";

import { useState, useEffect, useCallback } from "react";
import { MapPin, Loader2, Search } from "lucide-react";
import { cn } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import api from "@/lib/api";

export interface PlaceResult {
  placeId: string;
  name: string;
  formattedAddress: string;
  lat: number;
  lng: number;
}

interface GooglePlacesAutocompleteProps {
  value?: PlaceResult | null;
  onChange: (place: PlaceResult | null) => void;
  type?: "country" | "airport" | "city" | "zone" | "hotel";
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function GooglePlacesAutocomplete({
  value,
  onChange,
  type,
  placeholder = "Search Google Maps...",
  disabled = false,
  className,
}: GooglePlacesAutocompleteProps) {
  const [query, setQuery] = useState(value?.name || "");
  const [results, setResults] = useState<PlaceResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selected, setSelected] = useState(false);

  const searchPlaces = useCallback(
    async (q: string) => {
      if (q.trim().length < 2) {
        setResults([]);
        return;
      }
      setLoading(true);
      try {
        const params: Record<string, string> = { q: q.trim() };
        if (type) params.type = type;
        const { data } = await api.get("/locations/places-search", { params });
        const items = data.data || data || [];
        setResults(Array.isArray(items) ? items : []);
      } catch {
        setResults([]);
      } finally {
        setLoading(false);
      }
    },
    [type]
  );

  // Debounced search
  useEffect(() => {
    if (selected) return;
    const timer = setTimeout(() => {
      if (query.trim().length >= 2) {
        searchPlaces(query);
        setShowDropdown(true);
      } else {
        setResults([]);
        setShowDropdown(false);
      }
    }, 400);
    return () => clearTimeout(timer);
  }, [query, searchPlaces, selected]);

  // Sync external value
  useEffect(() => {
    if (value?.name && value.name !== query) {
      setQuery(value.name);
      setSelected(true);
    }
  }, [value?.name]); // eslint-disable-line react-hooks/exhaustive-deps

  function handleSelect(place: PlaceResult) {
    setQuery(place.name);
    setSelected(true);
    setShowDropdown(false);
    setResults([]);
    onChange(place);
  }

  function handleInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value;
    setQuery(val);
    setSelected(false);
    if (!val.trim()) {
      onChange(null);
      setResults([]);
      setShowDropdown(false);
    }
  }

  return (
    <div className={cn("relative", className)}>
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder={placeholder}
          value={query}
          onChange={handleInputChange}
          onFocus={() => {
            if (results.length > 0 && !selected) setShowDropdown(true);
          }}
          onBlur={() => {
            // Delay to allow click on dropdown item
            setTimeout(() => setShowDropdown(false), 200);
          }}
          disabled={disabled}
          className="border-border bg-card pl-9 pr-9 text-foreground placeholder:text-muted-foreground"
        />
        {loading && (
          <Loader2 className="absolute right-2.5 top-1/2 h-4 w-4 -translate-y-1/2 animate-spin text-muted-foreground" />
        )}
      </div>

      {showDropdown && results.length > 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-border bg-popover shadow-lg">
          <ul className="max-h-60 overflow-y-auto py-1">
            {results.map((place) => (
              <li key={place.placeId}>
                <button
                  type="button"
                  className="flex w-full items-start gap-2 px-3 py-2 text-left text-sm transition-colors hover:bg-accent"
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => handleSelect(place)}
                >
                  <MapPin className="mt-0.5 h-4 w-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate font-medium text-foreground">
                      {place.name}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {place.formattedAddress}
                    </p>
                  </div>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}

      {showDropdown && !loading && query.trim().length >= 2 && results.length === 0 && (
        <div className="absolute z-50 mt-1 w-full rounded-md border border-border bg-popover p-3 text-center text-sm text-muted-foreground shadow-lg">
          No places found
        </div>
      )}
    </div>
  );
}
