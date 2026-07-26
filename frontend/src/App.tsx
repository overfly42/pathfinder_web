import { Route, Routes } from 'react-router-dom';
import { CharacterSheetPage } from './pages/CharacterSheetPage';
import { CreationWizardPage } from './pages/CreationWizardPage';

function RouteStub({ label }: { label: string }) {
  return <p style={{ color: '#e2d3ab', padding: 24 }}>{label} — not built yet in this pass.</p>;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<CharacterSheetPage />} />
      <Route path="/create" element={<CreationWizardPage />} />
      <Route path="/levelup/:characterId" element={<RouteStub label="Stufenaufstieg" />} />
    </Routes>
  );
}

export default App;
