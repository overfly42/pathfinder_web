import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { apiGet, apiPost } from '../api/client';
import type { CharacterProgression } from '../types/characterProgression';
import type { User } from '../types/user';

interface AppStateValue {
  users: User[];
  currentUserId: string;
  setCurrentUserId: (id: string) => void;
  addUser: (name: string) => Promise<void>;

  /** Characters owned by currentUserId — what the header picker/sheet should offer. A new user
   *  starts with none (Requirement: users own characters, not the other way around). */
  visibleCharacterIds: string[];
  /** '' means the current user owns no characters yet. */
  currentCharacterId: string;
  setCurrentCharacterId: (id: string) => void;
  nameOverrides: Record<string, string>;
  renameCharacter: (id: string, name: string) => void;
  removeCharacter: (id: string) => void;

  getProgressionOverride: (id: string) => CharacterProgression | undefined;
  setProgressionOverride: (id: string, progression: CharacterProgression) => void;
}

const AppStateContext = createContext<AppStateValue | null>(null);

/** The two character fixtures the backend currently serves (`character_1.json`/`character_2.json`).
 *  Ownership isn't backed by a real `characters` table yet (that's roadmap slice 2), so these start
 *  unowned by any user — local session state layered on top, lost on reload like every other
 *  mutation in the app today. */
const INITIAL_CHARACTER_IDS = ['1', '2'];

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<User[]>([]);
  const [currentUserId, setCurrentUserIdState] = useState('');

  const [characterIds, setCharacterIds] = useState<string[]>(INITIAL_CHARACTER_IDS);
  const [characterOwners, setCharacterOwners] = useState<Record<string, string>>({});
  // Real (database-backed) characters owned by currentUserId, per `GET /api/users/{id}/characters`
  // (roadmap slice 2's follow-up) — kept separate from the fixture bookkeeping above since
  // ownership here is server-authoritative, not locally assigned.
  const [dbCharacterIds, setDbCharacterIds] = useState<string[]>([]);
  const [currentCharacterId, setCurrentCharacterId] = useState('');
  const [nameOverrides, setNameOverrides] = useState<Record<string, string>>({});
  const [progressionOverrides, setProgressionOverrides] = useState<Record<string, CharacterProgression>>({});

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
      return;
    }
    apiGet<{ id: string }[]>(`/api/users/${currentUserId}/characters`)
      .then((data) => {
        if (!cancelled) setDbCharacterIds(data.map((c) => c.id));
      })
      .catch((err: Error) => console.error('Failed to load characters', err));
    return () => {
      cancelled = true;
    };
  }, [currentUserId]);

  const visibleCharacterIds = useMemo(
    () => [...characterIds.filter((id) => characterOwners[id] === currentUserId), ...dbCharacterIds],
    [characterIds, characterOwners, currentUserId, dbCharacterIds],
  );

  // Keeps the current selection valid whenever the visible set changes (user switch, a character
  // getting removed, the db-characters fetch resolving, ...) — defaults to the first visible
  // character, or none.
  useEffect(() => {
    setCurrentCharacterId((current) => (visibleCharacterIds.includes(current) ? current : visibleCharacterIds[0] ?? ''));
  }, [visibleCharacterIds]);

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

  const getProgressionOverride = useCallback(
    (id: string) => progressionOverrides[id],
    [progressionOverrides],
  );

  const setProgressionOverride = useCallback((id: string, progression: CharacterProgression) => {
    setProgressionOverrides((prev) => ({ ...prev, [id]: progression }));
  }, []);

  const value = useMemo<AppStateValue>(
    () => ({
      users,
      currentUserId,
      setCurrentUserId,
      addUser,
      visibleCharacterIds,
      currentCharacterId,
      setCurrentCharacterId,
      nameOverrides,
      renameCharacter,
      removeCharacter,
      getProgressionOverride,
      setProgressionOverride,
    }),
    [
      users,
      currentUserId,
      setCurrentUserId,
      addUser,
      visibleCharacterIds,
      currentCharacterId,
      nameOverrides,
      renameCharacter,
      removeCharacter,
      getProgressionOverride,
      setProgressionOverride,
    ],
  );

  return <AppStateContext.Provider value={value}>{children}</AppStateContext.Provider>;
}

export function useAppState(): AppStateValue {
  const ctx = useContext(AppStateContext);
  if (!ctx) throw new Error('useAppState must be used within an AppStateProvider');
  return ctx;
}
