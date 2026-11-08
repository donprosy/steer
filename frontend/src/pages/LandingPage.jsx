import { useState } from "react";
import Icon from "../components/Icon.jsx";
import { Brand, Button } from "../components/UI.jsx";

const featureCards = [
  ["activity", "Sales, made simple", "See every sale in one place. Understand what's moving and what deserves your attention."],
  ["wallet", "Expenses under control", "Capture business costs by category and see how spending changes over time."],
  ["users", "Customer relationships", "Keep customer details and sales history organised as your business grows."],
  ["package", "Inventory clarity", "Know what you have in stock and spot low-stock items before they slow you down."],
  ["trend", "Performance insights", "Connect revenue, expenses and profit with reports built for everyday decisions."],
  ["sparkles", "A thoughtful AI partner", "Get help interpreting business trends with a text-based assistant, when you need it."],
];

const faqs = [
  ["What does Don Prosy Business Manager do?", "It brings everyday business records—customers, sales, expenses and inventory—into one clear workspace, with reporting designed to make performance easier to understand."],
  ["Who is it for?", "It is being designed for small business owners and entrepreneurs who want a practical view of how their business is doing."],
  ["How does the AI assistant work?", "The planned assistant will offer text-based help using business context you are authorised to access. AI features are not connected in this demonstration."],
  ["What subscription plans will be available?", "Starter, Growth and Business plans are planned. Pricing and final plan limits have not been set, so this preview intentionally uses placeholders."],
  ["How is my business data protected?", "Business data isolation and secure access are foundational requirements. Account security and production data services will be implemented in later development stages."],
  ["How can I get started?", "Explore the interface using the demo workspace. Registration and sign-in screens are demonstrations only and do not create an account yet."],
];

function DashboardPreview() {
  return (
    <div className="preview-frame">
      <div className="preview-top">
        <div className="preview-brand"><span className="brand__mark">d</span><span>Prosy</span></div>
        <span className="preview-chip"><i /> DEMO WORKSPACE</span>
        <span className="preview-avatar">JD</span>
      </div>
      <div className="preview-body">
        <div className="preview-greeting">
          <div><small>SATURDAY, NOVEMBER 7, 2026</small><h3>Good morning, James <span>✦</span></h3></div>
          <span className="preview-period">Last 30 days⌄</span>
        </div>
        <div className="preview-stats">
          <div><span>Total revenue</span><b>$24,580</b><em>↗ 12.8%</em></div>
          <div><span>Total expenses</span><b>$8,420</b><em className="muted">↘ 4.2%</em></div>
          <div><span>Net profit</span><b>$16,160</b><em>↗ 18.4%</em></div>
        </div>
        <div className="preview-lower">
          <div className="preview-chart">
            <div className="preview-chart__head"><b>Revenue overview</b><small>Last 6 months</small></div>
            <svg viewBox="0 0 400 112" preserveAspectRatio="none" aria-label="Decorative sample chart">
              <path d="M0 94 C35 82 44 59 82 71 S139 91 169 51 S227 70 255 40 S314 55 345 22 S380 35 400 8" fill="none" stroke="#3478f6" strokeWidth="3" />
              <path d="M0 94 C35 82 44 59 82 71 S139 91 169 51 S227 70 255 40 S314 55 345 22 S380 35 400 8 V112 H0Z" fill="url(#preview-gradient)" />
              <defs><linearGradient id="preview-gradient" x1="0" x2="0" y1="0" y2="1"><stop stopColor="#3478f6" stopOpacity=".16" /><stop offset="1" stopColor="#3478f6" stopOpacity="0" /></linearGradient></defs>
            </svg>
          </div>
          <div className="preview-ai"><span className="ai-orb"><Icon name="sparkles" size={17} /></span><small>PROSY AI INSIGHT</small><p>Revenue is trending up this month. Your top-selling products are driving the increase.</p><span>View business insights <Icon name="arrowRight" size={13} /></span></div>
        </div>
        <div className="preview-footer"><span>Recent transactions</span><span>View all →</span></div>
      </div>
    </div>
  );
}

function LandingPage({ navigate }) {
  const [menuOpen, setMenuOpen] = useState(false);
  const [billing, setBilling] = useState("monthly");
  const [openFaq, setOpenFaq] = useState(0);

  function go(path) {
    setMenuOpen(false);
    navigate(path);
  }

  return (
    <div className="marketing">
      <header className="marketing-nav">
        <div className="marketing-nav__inner">
          <a className="brand-link" href="/" onClick={(event) => { event.preventDefault(); go("/"); }}><Brand /></a>
          <button className="mobile-menu-toggle" aria-label={menuOpen ? "Close menu" : "Open menu"} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>
            <Icon name={menuOpen ? "close" : "menu"} />
          </button>
          <nav className={`marketing-links${menuOpen ? " marketing-links--open" : ""}`} aria-label="Main navigation">
            <a href="#home" onClick={() => setMenuOpen(false)}>Home</a>
            <a href="#features" onClick={() => setMenuOpen(false)}>Features</a>
            <a href="#how-it-works" onClick={() => setMenuOpen(false)}>How it works</a>
            <a href="#pricing" onClick={() => setMenuOpen(false)}>Pricing</a>
            <a href="#about" onClick={() => setMenuOpen(false)}>About</a>
            <div className="marketing-links__mobile-actions">
              <Button variant="text" onClick={() => go("/login")}>Log in</Button>
              <Button onClick={() => go("/register")}>Get started <Icon name="arrowRight" size={16} /></Button>
            </div>
          </nav>
          <div className="marketing-nav__actions">
            <button className="nav-login" onClick={() => go("/login")}>Log in</button>
            <Button className="nav-cta" onClick={() => go("/register")}>Get started <Icon name="arrowRight" size={16} /></Button>
          </div>
        </div>
      </header>

      <main>
        <section className="hero-section" id="home">
          <div className="hero-grid">
            <div className="hero-copy">
              <div className="hero-kicker"><span className="kicker-icon"><Icon name="sparkles" size={14} /></span> CLARITY FOR EVERY KIND OF BUSINESS</div>
              <h1>Run your business<br />smarter. <span>Grow with<br className="hero-break" /> confidence.</span></h1>
              <p className="hero-lede">The customers, sales, expenses and insights you need to move your business forward—all in one calm, clear workspace.</p>
              <div className="hero-actions">
                <Button onClick={() => go("/register")}>Get started for free <Icon name="arrowRight" size={17} /></Button>
                <a className="text-link" href="#features"><span className="play-icon">▶</span> Explore features</a>
              </div>
              <div className="hero-trust"><div className="trust-avatars"><AvatarMini initials="AM" /><AvatarMini initials="KO" /><AvatarMini initials="JD" /></div><p><strong>Made for the people behind small business.</strong><br /><span>Your next chapter starts with a clearer picture.</span></p></div>
            </div>
            <div className="hero-visual">
              <div className="hero-orbit hero-orbit--one" /><div className="hero-orbit hero-orbit--two" />
              <div className="floating-note floating-note--top"><span className="floating-icon floating-icon--green"><Icon name="trend" size={17} /></span><span><b>Business is moving</b><small>See your momentum clearly</small></span><i>↗</i></div>
              <DashboardPreview />
              <div className="floating-note floating-note--bottom"><span className="floating-icon floating-icon--blue"><Icon name="shield" size={17} /></span><span><b>Your business, in focus</b><small>One workspace. Less guesswork.</small></span></div>
            </div>
          </div>
          <div className="hero-bottom"><span>BUILT FOR THE EVERYDAY WORK OF RUNNING A BUSINESS</span><div><span><Icon name="briefcase" size={16} /> Business overview</span><span><Icon name="activity" size={16} /> Clear performance</span><span><Icon name="shield" size={16} /> Privacy by design</span></div></div>
        </section>

        <section className="section features-section" id="features">
          <div className="section-heading">
            <p className="eyebrow">EVERYTHING IN ITS RIGHT PLACE</p>
            <h2>More clarity. <span>Less juggling.</span></h2>
            <p>Running a business is a lot. Your tools should make the day feel lighter, not add another layer of work.</p>
          </div>
          <div className="feature-grid">
            {featureCards.map(([icon, title, description], index) => (
              <article className="feature-card" key={title}>
                <span className={`feature-icon feature-icon--${index + 1}`}><Icon name={icon} size={21} /></span>
                <h3>{title}</h3>
                <p>{description}</p>
                <span className="feature-arrow"><Icon name="arrowRight" size={16} /></span>
              </article>
            ))}
          </div>
        </section>

        <section className="section how-section" id="how-it-works">
          <div className="section-heading">
            <p className="eyebrow">SIMPLE BY DESIGN</p>
            <h2>A better view, in <span>three steps.</span></h2>
            <p>Start with what matters now. Build a clearer picture as you go.</p>
          </div>
          <div className="steps-grid">
            {[
              ["01", "Create your workspace", "Set up your business profile and make the space yours.", "briefcase"],
              ["02", "Bring your work together", "Organise customers, products, sales and expenses in one place.", "layers"],
              ["03", "Make your next move", "See how your business is doing and decide what comes next.", "trend"],
            ].map(([number, title, desc, icon]) => (
              <article className="step-card" key={number}><span className="step-number">{number}</span><div className="step-icon"><Icon name={icon} size={22} /></div><h3>{title}</h3><p>{desc}</p><div className="step-line" /></article>
            ))}
          </div>
        </section>

        <section className="dashboard-showcase" id="about">
          <div className="showcase-copy">
            <p className="eyebrow">YOUR BUSINESS AT A GLANCE</p>
            <h2>Know where you stand.<br /><span>See where you can go.</span></h2>
            <p>Thoughtful summaries bring the important numbers forward, so you can spend less time piecing things together and more time building what matters.</p>
            <ul className="showcase-list">
              <li><Icon name="check" size={17} />Revenue and expense trends, clearly presented</li>
              <li><Icon name="check" size={17} />Customer and inventory activity in context</li>
              <li><Icon name="check" size={17} />A demonstration workspace to explore the experience</li>
            </ul>
            <Button onClick={() => go("/app/overview")}>Explore the dashboard <Icon name="arrowRight" size={16} /></Button>
          </div>
          <div className="showcase-visual"><DashboardPreview /><div className="showcase-caption"><span className="demo-dot" />Illustrative preview · figures shown are sample data</div></div>
        </section>

        <section className="section pricing-section" id="pricing">
          <div className="section-heading">
            <p className="eyebrow">ROOM TO GROW</p>
            <h2>A plan for your <span>next chapter.</span></h2>
            <p>Start with the essentials. Choose more as your business grows. Pricing is being finalised.</p>
            <div className="billing-toggle" role="group" aria-label="Billing period">
              <button className={billing === "monthly" ? "is-active" : ""} onClick={() => setBilling("monthly")}>Monthly</button>
              <button className={billing === "yearly" ? "is-active" : ""} onClick={() => setBilling("yearly")}>Yearly <span>Save more</span></button>
            </div>
          </div>
          <div className="pricing-grid">
            {[
              ["Starter", "A thoughtful start for a business finding its rhythm.", "Essentials to get organised", ["Business dashboard", "Customer and product records", "Sales and expense tracking"]],
              ["Growth", "For owners ready to understand more and do more.", "More room to grow", ["Everything in Starter", "Inventory and business reports", "Text AI assistant allowance"]],
              ["Business", "More capability for a growing team and operation.", "Built for bigger ambitions", ["Everything in Growth", "Team access and permissions", "Expanded usage and insights"]],
            ].map(([name, desc, sub, items], i) => (
              <article className={`price-card${i === 1 ? " price-card--featured" : ""}`} key={name}>
                {i === 1 && <span className="popular-tag">A LITTLE MORE ROOM</span>}
                <div className="price-card__top"><span className={`plan-symbol plan-symbol--${i}`}><Icon name={i === 0 ? "layers" : i === 1 ? "trend" : "briefcase"} size={19} /></span><h3>{name}</h3></div>
                <p>{desc}</p>
                <div className="price-placeholder"><strong>Coming soon</strong><span>{billing === "monthly" ? "Monthly billing option planned" : "Annual billing option planned"}</span></div>
                <span className="price-sub">{sub}</span>
                <ul>{items.map((item) => <li key={item}><Icon name="check" size={15} />{item}</li>)}</ul>
                <Button variant={i === 1 ? "primary" : "outline"} onClick={() => go("/register")}>Explore {name} <Icon name="arrowRight" size={15} /></Button>
              </article>
            ))}
          </div>
          <p className="pricing-footnote"><Icon name="info" size={15} /> Monthly and yearly plan options are planned. Prices and final plan limits are not yet set.</p>
        </section>

        <section className="section faq-section" id="faq">
          <div className="faq-intro"><p className="eyebrow">GOOD QUESTIONS</p><h2>Curious? <span>We are too.</span></h2><p>Here are a few things worth knowing as we build.</p><a href="mailto:hello@donprosy.com">Have another question? Get in touch <Icon name="arrowRight" size={14} /></a></div>
          <div className="faq-list">
            {faqs.map(([question, answer], index) => <article className={`faq-item${openFaq === index ? " faq-item--open" : ""}`} key={question}>
              <button aria-expanded={openFaq === index} onClick={() => setOpenFaq(openFaq === index ? -1 : index)}><span>{question}</span><Icon name={openFaq === index ? "close" : "plus"} size={18} /></button>
              {openFaq === index && <p>{answer}</p>}
            </article>)}
          </div>
        </section>
      </main>

      <footer className="marketing-footer">
        <div className="footer-main">
          <div className="footer-brand"><Brand light /><p>A clearer way to understand and run your business. Built for the people who make it happen.</p><span className="footer-socials"><a href="mailto:hello@donprosy.com" aria-label="Email us"><Icon name="message" size={17} /></a><a href="#home" aria-label="Back to top"><Icon name="arrowRight" size={17} /></a></span></div>
          <div className="footer-column"><b>PRODUCT</b><a href="#features">Features</a><a href="#how-it-works">How it works</a><a href="#pricing">Pricing</a><button onClick={() => go("/app/overview")}>Demo workspace</button></div>
          <div className="footer-column"><b>COMPANY</b><a href="#about">About Don Prosy</a><a href="#faq">FAQs</a><a href="mailto:hello@donprosy.com">Contact</a></div>
          <div className="footer-column"><b>RESOURCES</b><a href="#faq">Help & support</a><a href="#faq">Privacy policy</a><a href="#faq">Terms of service</a></div>
        </div>
        <div className="footer-bottom"><span>© 2026 Don Prosy Business Manager. Built for the next chapter.</span><span><i /> Thoughtfully made for small business.</span></div>
      </footer>
    </div>
  );
}

function AvatarMini({ initials }) {
  return <span className="avatar-mini">{initials}</span>;
}

export default LandingPage;
