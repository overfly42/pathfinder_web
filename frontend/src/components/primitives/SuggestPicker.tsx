import { useState } from 'react';

export interface SuggestPickerSuggestion {
  id: string;
  label: string;
}

interface SuggestPickerProps {
  suggestions: SuggestPickerSuggestion[];
  /** Currently picked catalog suggestion, or `null` if the player typed a
   *  custom value instead — mutually exclusive with `customText` being
   *  non-empty, same "exactly one of two" invariant the backend's
   *  `SkillRankSelection` enforces. Enforcing which one wins on each change
   *  is the caller's job (see `onPickSuggestion`/`onChangeCustomText`). */
  pickedSuggestionId: string | null;
  customText: string;
  onPickSuggestion: (id: string) => void;
  onChangeCustomText: (text: string) => void;
  searchPlaceholder: string;
  customPlaceholder: string;
}

/** "Pick from a suggested catalog value, or type your own" — no existing
 *  combobox/freeform-entry pattern in this codebase to extend, so this
 *  mirrors `PickList.tsx`'s visual language (search input + chip row)
 *  instead of a native `<datalist>`, for consistency with the rest of the
 *  wizard. Currently only used for skill specializations
 *  (Handwerk/Beruf/Auftreten), but kept generic in case another feature
 *  needs the same "suggestions or free text" shape later. */
export function SuggestPicker({
  suggestions,
  pickedSuggestionId,
  customText,
  onPickSuggestion,
  onChangeCustomText,
  searchPlaceholder,
  customPlaceholder,
}: SuggestPickerProps) {
  const [query, setQuery] = useState('');
  const filtered = suggestions.filter((s) => s.label.toLowerCase().includes(query.toLowerCase()));

  return (
    <>
      {suggestions.length > 0 && (
        <>
          <div className="wizard-search">
            <input type="text" placeholder={searchPlaceholder} value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <div className="chip-row" style={{ marginBottom: 10 }}>
            {filtered.map((suggestion) => (
              <button
                key={suggestion.id}
                type="button"
                className={`chip${pickedSuggestionId === suggestion.id ? ' active' : ''}`}
                onClick={() => onPickSuggestion(suggestion.id)}
              >
                {suggestion.label}
              </button>
            ))}
          </div>
        </>
      )}
      <div className="wizard-search">
        <input
          type="text"
          placeholder={customPlaceholder}
          value={customText}
          onChange={(e) => onChangeCustomText(e.target.value)}
        />
      </div>
    </>
  );
}
