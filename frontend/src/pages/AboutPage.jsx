export default function AboutPage() {
  return (
    <div className="page page--pad">
      <header className="page__header">
        <div>
          <h1 className="workspace__brand">About</h1>
          <p className="workspace__sub">How the analytics assistant works</p>
        </div>
      </header>

      <div className="about-grid">
        <section className="about-block">
          <h2>1. Ask in English</h2>
          <p>
            Type a business question on Ask. Example prompts cover revenue, orders,
            customers, and reviews.
          </p>
        </section>
        <section className="about-block">
          <h2>2. Retrieve context</h2>
          <p>
            ChromaDB finds related table descriptions and similar past questions so
            the model knows which tables to use.
          </p>
        </section>
        <section className="about-block">
          <h2>3. Generate & run SQL</h2>
          <p>
            Groq writes a SQL query behind the scenes. It runs against the local
            SQLite e-commerce database — you only see the answer table.
          </p>
        </section>
        <section className="about-block">
          <h2>4. Learn from success</h2>
          <p>
            Successful questions are saved back into Chroma as few-shot examples,
            improving later answers in the same environment.
          </p>
        </section>
      </div>
    </div>
  )
}
