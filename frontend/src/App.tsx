import { Route, Routes } from 'react-router-dom';
import { CharacterSheetPage } from './pages/CharacterSheetPage';
import { CreationWizardPage } from './pages/CreationWizardPage';
import { LevelUpWizardPage } from './pages/LevelUpWizardPage';

function App() {
  return (
    <Routes>
      <Route path="/" element={<CharacterSheetPage />} />
      <Route path="/create" element={<CreationWizardPage />} />
      <Route path="/levelup/:characterId" element={<LevelUpWizardPage />} />
    </Routes>
  );
}

export default App;
