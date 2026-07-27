import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from 'react';
import { createId } from '../lib/id';
import type { CharacterProgression } from '../types/characterProgression';

export interface MockUser {
  id: string;
  name: string;
}

interface AppStateValue {
  users: MockUser[];
  currentUserId: string;
  setCurrentUserId: (id: string) => void;
  addUser: (name: string) => void;

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

/** The two character fixtures the backend currently serves (`character_1.json`/`character_2.json`),
 *  both owned by the seed user. Local-only session state layered on top — nothing here is
 *  persisted to the backend, matching every other mutation in the app today; it's lost on reload. */
const INITIAL_USER_ID = 'u1';
const INITIAL_CHARACTER_IDS = ['1', '2'];

export function AppStateProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<MockUser[]>([{ id: INITIAL_USER_ID, name: 'Anna' }]);
  const [currentUserId, setCurrentUserIdState] = useState(INITIAL_USER_ID);

  const [characterIds, setCharacterIds] = useState<string[]>(INITIAL_CHARACTER_IDS);
  const [characterOwners, setCharacterOwners] = useState<Record<string, string>>({
    '1': INITIAL_USER_ID,
    '2': INITIAL_USER_ID,
  });
  const [currentCharacterId, setCurrentCharacterId] = useState(INITIAL_CHARACTER_IDS[0]);
  const [nameOverrides, setNameOverrides] = useState<Record<string, string>>({});
  const [progressionOverrides, setProgressionOverrides] = useState<Record<string, CharacterProgression>>({});

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

  const addUser = useCallback((name: string) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const id = createId();
    setUsers((prev) => [...prev, { id, name: trimmed }]);
    setCurrentUserIdState(id);
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
