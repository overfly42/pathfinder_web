import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { useSearchParams } from 'react-router-dom';
import { apiGet, apiPost } from '../api/client';
import type { User } from '../types/user';
import type { Language } from '../lib/spellComponents';

interface AppStateValue {
  /** UI language (header dropdown). Only drives pieces that already have a translation table
   *  (e.g. `lib/spellComponents.ts`); remaining UI text is still German-only. */
  language: Language;
  setLanguage: (language: Language) => void;
  users: User[];
  currentUserId: string;
  setCurrentUserId: (id: string) => void;
  addUser: (name: string) => Promise<void>;

  /** Characters owned by currentUserId — what the header picker/sheet should offer. A new user
   *  starts with none (Requirement: users own characters, not the other way around). */
  visibleCharacterIds: string[];
  /** `visibleCharacterIds` minus companions (backend `master_character_id` set) — what the
   *  character picker lists. A companion is reached from its master's sheet or its own URL,
   *  and stays a valid selection because it's still in `visibleCharacterIds`. */
  pickerCharacterIds: string[];
  /** Re-fetches the current user's character list — after creating a companion, so its new id
   *  counts as a valid selection before switching to it. */
  reloadCharacters: () => void;
  /** '' means the current user owns no characters yet. */
  currentCharacterId: string;
  setCurrentCharacterId: (id: string) => void;
  nameOverrides: Record<string, string>;
  renameCharacter: (id: string, name: string) => void;
  removeCharacter: (id: string) => void;
}

const AppStateContext = createContext<AppStateValue | null>(null);

/** The two character fixtures the backend currently serves (`character_1.json`/`character_2.json`).
 *  Ownership isn't backed by a real `characters` table yet (that's roadmap slice 2), so these start
 *  unowned by any user — local session state layered on top, lost on reload like every other
 *  mutation in the app today. */
const INITIAL_CHARACTER_IDS = ['1', '2'];

export function AppStateProvider({ children }: { children: ReactNode }) {
  // `user`/`character` query params are the source of truth for the initial
  // selection (a mobile reload, a bookmark, or an "Add to Home Screen"
  // shortcut all re-navigate to this same URL) — every subsequent selection
  // change is mirrored back into them below, so the URL never drifts from
  // what's actually shown.
  const [searchParams, setSearchParams] = useSearchParams();
  const [users, setUsers] = useState<User[]>([]);
  const [language, setLanguageState] = useState<Language>(() => {
    try {
      return localStorage.getItem('language') === 'en' ? 'en' : 'de';
    } catch {
      return 'de';
    }
  });
  const setLanguage = useCallback((next: Language) => {
    setLanguageState(next);
    try {
      localStorage.setItem('language', next);
    } catch {
      // storage unavailable (private mode): the choice just doesn't persist
    }
  }, []);
  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);
  const [currentUserId, setCurrentUserIdState] = useState(() => searchParams.get('user') ?? '');

  const [characterIds, setCharacterIds] = useState<string[]>(INITIAL_CHARACTER_IDS);
  const [characterOwners, setCharacterOwners] = useState<Record<string, string>>({});
  // Real (database-backed) characters owned by currentUserId, per `GET /api/users/{id}/characters`
  // (roadmap slice 2's follow-up) — kept separate from the fixture bookkeeping above since
  // ownership here is server-authoritative, not locally assigned.
  const [dbCharacterIds, setDbCharacterIds] = useState<string[]>([]);
  const [companionIds, setCompanionIds] = useState<Set<string>>(new Set());
  const [charactersReloadKey, setCharactersReloadKey] = useState(0);
  // Whether dbCharacterIds reflects currentUserId yet — the "keep selection
  // valid" effect below must not treat a URL-supplied currentCharacterId as
  // invalid just because this fetch hasn't resolved yet (it starts `[]` on
  // every user switch, which would otherwise look identical to "this
  // character doesn't belong to this user").
  const [charactersLoaded, setCharactersLoaded] = useState(false);
  const [currentCharacterId, setCurrentCharacterId] = useState(() => searchParams.get('character') ?? '');
  const [nameOverrides, setNameOverrides] = useState<Record<string, string>>({});

  useEffect(() => {
    let cancelled = false;
    apiGet<User[]>('/api/users')
      .then((data) => {
        if (!cancelled) setUsers(data);
      })
      .catch((err: Error) => console.error('Failed to load users', err));
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    if (!currentUserId) {
      setDbCharacterIds([]);
      setCharactersLoaded(true);
      return;
    }
    setCharactersLoaded(false);
    apiGet<{ id: string; master_character_id: string | null }[]>(`/api/users/${currentUserId}/characters`)
      .then((data) => {
        if (!cancelled) {
          setDbCharacterIds(data.map((c) => c.id));
          setCompanionIds(new Set(data.filter((c) => c.master_character_id).map((c) => c.id)));
          setCharactersLoaded(true);
        }
      })
      .catch((err: Error) => {
        console.error('Failed to load characters', err);
        if (!cancelled) setCharactersLoaded(true);
      });
    return () => {
      cancelled = true;
    };
  }, [currentUserId, charactersReloadKey]);

  const reloadCharacters = useCallback(() => setCharactersReloadKey((key) => key + 1), []);

  const visibleCharacterIds = useMemo(
    () => [...characterIds.filter((id) => characterOwners[id] === currentUserId), ...dbCharacterIds],
    [characterIds, characterOwners, currentUserId, dbCharacterIds],
  );
  const pickerCharacterIds = useMemo(
    () => visibleCharacterIds.filter((id) => !companionIds.has(id)),
    [visibleCharacterIds, companionIds],
  );

  // Keeps the current selection valid whenever the visible set changes (user switch, a character
  // getting removed, the db-characters fetch resolving, ...) — defaults to the first visible
  // character, or none. Skipped while `charactersLoaded` is still false so a URL-supplied
  // currentCharacterId survives the moment between mount and that fetch resolving.
  useEffect(() => {
    if (!charactersLoaded) return;
    setCurrentCharacterId((current) => (visibleCharacterIds.includes(current) ? current : pickerCharacterIds[0] ?? ''));
  }, [visibleCharacterIds, pickerCharacterIds, charactersLoaded]);

  // Mirrors the current selection into the URL (replacing, not pushing, so
  // switching users/characters doesn't fill up the back-button history).
  useEffect(() => {
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (currentUserId) next.set('user', currentUserId);
        else next.delete('user');
        if (currentCharacterId) next.set('character', currentCharacterId);
        else next.delete('character');
        return next;
      },
      { replace: true },
    );
  }, [currentUserId, currentCharacterId, setSearchParams]);

  const setCurrentUserId = useCallback((id: string) => {
    setCurrentUserIdState(id);
  }, []);

  const addUser = useCallback(async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const created = await apiPost<User>('/api/users', { name: trimmed });
    setUsers((prev) => [...prev, created]);
    setCurrentUserIdState(created.id);
  }, []);

  const renameCharacter = useCallback((id: string, name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setNameOverrides((prev) => ({ ...prev, [id]: trimmed }));
  }, []);

  const removeCharacter = useCallback((id: string) => {
    setCharacterIds((prev) => prev.filter((existing) => existing !== id));
    setCharacterOwners((prev) => {
      const next = { ...prev };
      delete next[id];
      return next;
    });
    setDbCharacterIds((prev) => prev.filter((existing) => existing !== id));
  }, []);

  const value = useMemo<AppStateValue>(
    () => ({
      language,
      setLanguage,
      users,
      currentUserId,
      setCurrentUserId,
      addUser,
      visibleCharacterIds,
      pickerCharacterIds,
      reloadCharacters,
      currentCharacterId,
      setCurrentCharacterId,
      nameOverrides,
      renameCharacter,
      removeCharacter,
    }),
    [
      language,
      setLanguage,
      users,
      currentUserId,
      setCurrentUserId,
      addUser,
      visibleCharacterIds,
      pickerCharacterIds,
      reloadCharacters,
      currentCharacterId,
      nameOverrides,
      renameCharacter,
      removeCharacter,
    ],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppStateValue {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within an AppStateProvider');
  return ctx;
}
