import { Route, Routes } from 'react-router-dom';
import { CharacterSheetPage } from './pages/CharacterSheetPage';

function RouteStub({ label }: { label: string }) {
  return <p style={{ color: '#e2d3ab', padding: 24 }}>{label} — not built yet in this pass.</p>;
}

function App() {
  return (
    <Routes>
      <Route path="/" element={<CharacterSheetPage />} />
      <Route path="/create" element={<RouteStub label="Charaktererstellung" />} />
      <Route path="/levelup/:characterId" element={<RouteStub label="Stufenaufstieg" />} />
    </Routes>
  );
}

export default App;
