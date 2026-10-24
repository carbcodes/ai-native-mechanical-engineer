import { useEffect, useRef, useState } from "react";
import { useReducedMotion } from "motion/react";
import { ArrowUpRight, ChevronDown, ExternalLink, Menu, X } from "lucide-react";
import Journey from "./components/Journey";

const PRICING_URL =
  "https://www.vibewrite.work/pricing?utm_source=mechy&utm_medium=landing&utm_campaign=mechy_demo";
const DEMO_EMAIL =
  "mailto:hello@example.com?subject=My%20Mechy%20demo&body=Hi%2C%0A%0AI%27d%20love%20to%20try%20Mechy.%0A%0AMy%20VibeWrite%20Pro%20account%20email%3A%20%0AThe%20hardware%20project%20I%27m%20working%20on%3A%20%0A%0AThanks!";

function Mark({ className = "" }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
    >
      <path
        d="m16 2 12.1 7v14L16 30 3.9 23V9L16 2Z"
        stroke="currentColor"
        strokeWidth="2.5"
      />
      <path
        d="M9 22V12h4v2c1.5-3.3 5-3.2 6 0 2.3-3.3 6-1.8 6 1v7h-4v-6c0-1.8-2-1.8-2 0v6h-4v-6c0-1.8-2-1.8-2 0v6H9Z"
        fill="currentColor"
        transform="translate(-1.5 0)"
      />
    </svg>
  );
}

function PurchaseDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const el = dialog.current;
    if (!el) return;
    if (open) {
      el.showModal();
      document.body.style.overflow = "hidden";
    } else {
      el.close();
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [open]);
  return (
    <dialog
      className="purchase-dialog"
      ref={dialog}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
      aria-labelledby="checkout-title"
    >
      <div className="dialog-content">
        <button
          className="icon-button dialog-close"
          onClick={onClose}
          aria-label="Close demo details"
        >
          <X size={22} />
        </button>
        <Mark className="dialog-mark" />
        <span className="eyebrow">A SEAT AT THE WORKBENCH</span>
        <h2 id="checkout-title">
          Bring your
          <br />
          next big idea.
        </h2>
        <p>
          Use VibeWrite Pro to get started, then arrange your Mechy demo
          directly with our founder.
        </p>
        <div className="dialog-price">
          <strong>$19.99</strong>
          <span>
            USD / month
            <br />
            Recurring VibeWrite Pro subscription
          </span>
        </div>
        <ol className="checkout-steps">
          <li>
            <span>01</span>
            <div>
              <strong>Subscribe to VibeWrite Pro.</strong>
              <p>
                Choose the Pro plan and Monthly billing on the next page. Sign
                in or create your VibeWrite account.
              </p>
            </div>
          </li>
          <li>
            <span>02</span>
            <div>
              <strong>Bring us your project.</strong>
              <p>
                <a href={DEMO_EMAIL}>
                  Email us to arrange your demo <ArrowUpRight size={13} />
                </a>{" "}
                using the email on your Pro account.
              </p>
            </div>
          </li>
        </ol>
        <a
          className="button button-blue button-full"
          href={PRICING_URL}
          target="_blank"
          rel="noopener noreferrer"
        >
          Continue to VibeWrite <ArrowUpRight size={18} />
        </a>
        <p className="checkout-disclosure">
          Mechy is in early development. This purchases VibeWrite Pro; Mechy
          access and demo scheduling are arranged separately. Manage or cancel
          your subscription in VibeWrite.
        </p>
      </div>
    </dialog>
  );
}

const faqs = [
  {
    q: "What am I paying for today?",
    a: "VibeWrite Pro at $19.99/month, with your Mechy demo arranged separately by email; purchasing does not automatically provision a Mechy engineering workspace.",
  },
  {
    q: "Is the engineering workspace ready?",
    a: "Mechy is in development, and the workshop is an illustrative preview of the planned sketching, physics, FEA, CAD/CAM, and sourcing tools.",
  },
  {
    q: "Where will the parts come from?",
    a: "The planned agent will compare compatible components from suppliers such as McMaster-Carr, Pololu, and DigiKey against your design requirements and budget.",
  },
];

export default function App() {
  const reduced = Boolean(useReducedMotion());
  const [checkout, setCheckout] = useState(false);
  const [menu, setMenu] = useState(false);
  useEffect(() => {
    function closeOnEscape(event: KeyboardEvent) {
      if (event.key === "Escape") setMenu(false);
    }
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, []);
  return (
    <>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="site-header">
        <a href="#" className="brand" aria-label="Mechy home">
          <Mark />
          <span>mechy</span>
        </a>
        <nav className={menu ? "nav-open" : ""} aria-label="Main navigation">
          <a href="#workbench" onClick={() => setMenu(false)}>
            The workshop
          </a>
          <a href="#pricing" onClick={() => setMenu(false)}>
            Your next build
          </a>
        </nav>
        <div className="header-actions">
          <button
            className="button button-small"
            onClick={() => setCheckout(true)}
          >
            Get the demo <ArrowUpRight size={16} />
          </button>
          <button
            className="icon-button menu-toggle"
            onClick={() => setMenu(!menu)}
            aria-label={menu ? "Close navigation" : "Open navigation"}
            aria-expanded={menu}
          >
            {menu ? <X size={23} /> : <Menu size={23} />}
          </button>
        </div>
      </header>
      <main id="main">
        <Journey reduced={reduced} />
        <section className="demo-section" id="pricing">
          <div className="demo-intro">
            <h2>
              What will
              <br />
              you make?
            </h2>
            <p>
              Bring Claude or Codex to your engineering workspace, with
              VibeWrite for your project notes.
            </p>
          </div>
          <div className="demo-offer">
            <span className="offer-label">THE MECHY DEMO</span>
            <div className="price">
              <strong>$19.99</strong>
              <span>USD / month</span>
            </div>
            <p>Through your VibeWrite Pro subscription.</p>
            <button className="button" onClick={() => setCheckout(true)}>
              Bring your project <ArrowUpRight size={18} />
            </button>
            <small>
              Recurring subscription · Cancel in VibeWrite
              <br />
              Mechy demo arranged separately.
            </small>
          </div>
          <div className="faq-list">
            {faqs.map((item) => (
              <details key={item.q}>
                <summary>
                  {item.q}
                  <ChevronDown size={16} />
                </summary>
                <p>{item.a}</p>
              </details>
            ))}
          </div>
        </section>
      </main>
      <footer>
        <a href="#workbench" className="brand">
          <Mark />
          <span>mechy</span>
        </a>
        <span>For garage makers and hardware teams.</span>
        <div>
          <a
            href="https://www.vibewrite.work"
            target="_blank"
            rel="noopener noreferrer"
          >
            VibeWrite <ExternalLink size={12} />
          </a>
          <a href="mailto:hello@example.com">
            Say hello <ArrowUpRight size={14} />
          </a>
        </div>
      </footer>
      <PurchaseDialog open={checkout} onClose={() => setCheckout(false)} />
    </>
  );
}
