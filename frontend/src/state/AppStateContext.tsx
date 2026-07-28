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

  const visibleCharacterIds = useMemo(
    () => characterIds.filter((id) => characterOwners[id] === currentUserId),
    [characterIds, characterOwners, currentUserId],
  );

  const setCurrentUserId = useCallback(
    (id: string) => {
      setCurrentUserIdState(id);
      const owned = characterIds.filter((cid) => characterOwners[cid] === id);
      setCurrentCharacterId(owned[0] ?? '');
    },
    [characterIds, characterOwners],
  );

  const addUser = useCallback(async (name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const created = await apiPost<User>('/api/users', { name: trimmed });
    setUsers((prev) => [...prev, created]);
    setCurrentUserIdState(created.id);
    // A freshly created user owns no characters yet — don't leak the previous user's selection.
    setCurrentCharacterId('');
  }, []);

  const renameCharacter = useCallback((id: string, name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    setNameOverrides((prev) => ({ ...prev, [id]: trimmed }));
  }, []);

  const removeCharacter = useCallback(
    (id: string) => {
      const nextIds = characterIds.filter((existing) => existing !== id);
      const nextOwners = { ...characterOwners };
      delete nextOwners[id];
      setCharacterIds(nextIds);
      setCharacterOwners(nextOwners);
      setCurrentCharacterId((current) => {
        if (current !== id) return current;
        const stillOwned = nextIds.filter((cid) => nextOwners[cid] === currentUserId);
        return stillOwned[0] ?? '';
      });
    },
    [characterIds, characterOwners, currentUserId],
  );

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
