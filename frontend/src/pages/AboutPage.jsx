export default function AboutPage() {
  return (
    <div className="page page--pad">
      <header className="page__header">
        <div>
          <h1 className="workspace__brand">About</h1>
          <p className="workspace__sub">What this assistant helps you do</p>
        </div>
      </header>

      <div className="about-grid">
        <section className="about-block">
          <h2>Ask everyday questions</h2>
          <p>
            Type questions the way you’d ask a colleague about sales, products,
            customers, or reviews, and get a clear answer back.
          </p>
        </section>
        <section className="about-block">
          <h2>See results as a table</h2>
          <p>
            Answers show up as simple tables you can scan quickly, so you can
            spot trends without digging through reports.
          </p>
        </section>
        <section className="about-block">
          <h2>Ask about yourself</h2>
          <p>
            You have your own orders and reviews in the store, so you can ask
            things like how much you’ve spent or what you bought last.
          </p>
        </section>
        <section className="about-block">
          <h2>Come back to past questions</h2>
          <p>
            History keeps every question you’ve asked, so you can revisit or ask
            them again whenever you like.
          </p>
        </section>
      </div>
    </div>
  )
}
