import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/ui'
import Dashboard from './pages/Dashboard'
import Repositories from './pages/Repositories'
import ReviewDetail from './pages/ReviewDetail'
import Reviews from './pages/Reviews'

const qc = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchInterval: 15_000 } },
})

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Layout>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/reviews" element={<Reviews />} />
            <Route path="/reviews/:id" element={<ReviewDetail />} />
            <Route path="/repositories" element={<Repositories />} />
          </Routes>
        </Layout>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
