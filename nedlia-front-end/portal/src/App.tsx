/**
 * Main application component.
 */
export function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow">
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <h1 className="text-3xl font-bold tracking-tight text-gray-900">
            Nedlia Portal
          </h1>
        </div>
      </header>
      <main>
        <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
          <p className="text-gray-600">
            Welcome to the Nedlia product placement SaaS platform. Please login
            to continue. This is currently a beta version of the platform.
          </p>
        </div>
      </main>
    </div>
  );
}
