import { Route, Routes } from 'react-router';

import { HomePage } from './pages/HomePage';
import { LoginPage } from './pages/LoginPage';

/** The app's routes. T5.3 adds the remaining pages, guards and a 404. */
export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/" element={<HomePage />} />
    </Routes>
  );
}
