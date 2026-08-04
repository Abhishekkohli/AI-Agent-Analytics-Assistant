import { useState } from 'react'

const ENTITIES = {
  categories: {
    label: 'Categories',
    blurb: 'Product groupings by department (e.g. Tech, Apparel).',
  },
  products: {
    label: 'Products',
    blurb: 'Items in the catalog — priced and stocked under a category.',
  },
  customers: {
    label: 'Customers',
    blurb: 'People who place orders and leave product reviews.',
  },
  orders: {
    label: 'Orders',
    blurb: 'A customer purchase with status and total amount.',
  },
  order_items: {
    label: 'Order items',
    blurb: 'Line items that link an order to the products it contains.',
  },
  reviews: {
    label: 'Reviews',
    blurb: 'Star ratings left by customers on products they’ve bought.',
  },
}

const FLOWS = [
  'A customer places an order.',
  'Each order is made of order items.',
  'Order items point at products from the catalog.',
  'Products belong to categories.',
  'Customers can also leave reviews on products.',
]

export default function ExplorePage() {
  const [active, setActive] = useState('orders')
  const selected = ENTITIES[active]

  return (
    <div className="page page--pad">
      <header className="page__header">
        <div>
          <h1 className="workspace__brand">Explore</h1>
          <p className="workspace__sub">
            High-level view of the order-management domain — not the raw database schema
          </p>
        </div>
      </header>

      <div className="domain">
        <section className="domain__diagram" aria-label="Order management entity diagram">
          <svg viewBox="0 0 720 420" role="img" className="domain__svg">
            <title>Order management entities and relationships</title>
            <defs>
              <marker
                id="arrow"
                viewBox="0 0 10 10"
                refX="9"
                refY="5"
                markerWidth="7"
                markerHeight="7"
                orient="auto-start-reverse"
              >
                <path d="M 0 0 L 10 5 L 0 10 z" fill="#6b7c78" />
              </marker>
            </defs>

            {/* Relationship lines */}
            <g className="domain__edges" stroke="#6b7c78" strokeWidth="1.6" fill="none">
              {/* categories → products */}
              <line x1="160" y1="78" x2="160" y2="118" markerEnd="url(#arrow)" />
              {/* customers → orders */}
              <line x1="440" y1="155" x2="460" y2="155" markerEnd="url(#arrow)" />
              {/* orders → order_items */}
              <line x1="540" y1="180" x2="540" y2="300" markerEnd="url(#arrow)" />
              {/* order_items → products */}
              <path d="M 460 325 C 360 325, 280 220, 240 180" markerEnd="url(#arrow)" />
              {/* customers → reviews */}
              <path d="M 320 180 C 280 220, 240 280, 240 300" markerEnd="url(#arrow)" />
              {/* products → reviews */}
              <line x1="160" y1="180" x2="180" y2="300" markerEnd="url(#arrow)" />

              <text x="168" y="105" className="domain__edge-label">
                groups
              </text>
              <text x="442" y="145" className="domain__edge-label">
                places
              </text>
              <text x="548" y="245" className="domain__edge-label">
                contains
              </text>
              <text x="300" y="250" className="domain__edge-label">
                includes
              </text>
              <text x="250" y="270" className="domain__edge-label">
                writes
              </text>
              <text x="100" y="250" className="domain__edge-label">
                about
              </text>
            </g>

            {/* Nodes */}
            {[
              { id: 'categories', x: 80, y: 28, w: 160, h: 50 },
              { id: 'products', x: 80, y: 130, w: 160, h: 50 },
              { id: 'customers', x: 280, y: 130, w: 160, h: 50 },
              { id: 'orders', x: 460, y: 130, w: 160, h: 50 },
              { id: 'order_items', x: 460, y: 300, w: 160, h: 50 },
              { id: 'reviews', x: 120, y: 300, w: 160, h: 50 },
            ].map((node) => {
              const isActive = active === node.id
              return (
                <g
                  key={node.id}
                  className={`domain__node${isActive ? ' is-active' : ''}`}
                  role="button"
                  tabIndex={0}
                  onClick={() => setActive(node.id)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault()
                      setActive(node.id)
                    }
                  }}
                  style={{ cursor: 'pointer' }}
                >
                  <rect
                    x={node.x}
                    y={node.y}
                    width={node.w}
                    height={node.h}
                    rx="12"
                    className="domain__node-shape"
                  />
                  <text
                    x={node.x + node.w / 2}
                    y={node.y + node.h / 2 + 5}
                    textAnchor="middle"
                    className="domain__node-label"
                  >
                    {ENTITIES[node.id].label}
                  </text>
                </g>
              )
            })}
          </svg>
        </section>

        <aside className="domain__aside">
          <div className="domain__card">
            <p className="domain__eyebrow">Selected entity</p>
            <h2>{selected.label}</h2>
            <p>{selected.blurb}</p>
          </div>

          <div className="domain__card">
            <p className="domain__eyebrow">How it fits together</p>
            <ol className="domain__flow">
              {FLOWS.map((step) => (
                <li key={step}>{step}</li>
              ))}
            </ol>
          </div>
        </aside>
      </div>
    </div>
  )
}
