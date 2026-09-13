import { BrowserRouter, Route, Routes } from 'react-router-dom'
import Layout from './Layout'
import Theory from './Theory'
import HomePage from './pages/HomePage'
import DebuggerPage from './pages/DebuggerPage'
import HistoryPage from './pages/HistoryPage'
import QuizPage from './pages/QuizPage'
import AboutPage from './pages/AboutPage'
import HelpPage from './pages/HelpPage'
import LearnPage from './pages/LearnPage'
import { ThemeProvider } from './ThemeContext'
import './theme.css'
import './App.css'

function TheoryPage() {
  return (
    <section className="theory-page">
      <h1>Theory</h1>
      <Theory />
    </section>
  )
}

function App() {
  return (
    <ThemeProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/debugger" element={<DebuggerPage />} />
            <Route path="/theory" element={<TheoryPage />} />
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
