import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import Layout from './Layout'
import HomePage from './pages/HomePage'
import ComparePage from './pages/ComparePage'
import SqlConsolePage from './pages/SqlConsolePage'
import TestRunnerPage from './pages/TestRunnerPage'
import HistoryPage from './pages/HistoryPage'
import QuizPage from './pages/QuizPage'
import AboutPage from './pages/AboutPage'
import HelpPage from './pages/HelpPage'
import LearnPage from './pages/LearnPage'
import { ThemeProvider } from './ThemeContext'
import './theme.css'
import './App.css'

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            {/* The Debugger and SQL Console pages merged into one --
                see SqlConsolePage.jsx's own module comment. /debugger
                redirects rather than 404ing, for anyone with an old
                bookmark/link. */}
            <Route path="/debugger" element={<Navigate to="/sql-console" replace />} />
            <Route path="/compare" element={<ComparePage />} />
            <Route path="/sql-console" element={<SqlConsolePage />} />
            <Route path="/tests" element={<TestRunnerPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/quiz" element={<QuizPage />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/help" element={<HelpPage />} />
            <Route path="/learn" element={<LearnPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ThemeProvider>
  )
}

export default App
