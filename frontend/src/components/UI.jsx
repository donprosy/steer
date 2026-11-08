import { useEffect } from "react";
import Icon from "./Icon.jsx";

export function Brand({ light = false }) {
  return (
    <span className={`brand${light ? " brand--light" : ""}`}>
      <span className="brand__mark">S</span>
      <span className="brand__name">
        STEER<span>BUSINESS PLATFORM</span>
      </span>
    </span>
  );
}

export function Button({
  children,
  variant = "primary",
  icon,
  className = "",
  ...props
}) {
  return (
    <button className={`button button--${variant} ${className}`} {...props}>
      {icon && <Icon name={icon} size={17} />}
      {children}
    </button>
  );
}

export function DemoNotice({ children = "Demonstration data · not connected to a live business" }) {
  return (
    <div className="demo-notice">
      <span className="demo-notice__dot" />
      {children}
    </div>
  );
}

export function Avatar({ initials = "JD", color = "blue", small = false }) {
  return (
    <span className={`avatar avatar--${color}${small ? " avatar--small" : ""}`}>
      {initials}
    </span>
  );
}

export function Modal({ title, onClose, children }) {
  useEffect(() => {
    function onKeyDown(event) {
      if (event.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [onClose]);

  return (
    <div className="modal-backdrop" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        className="modal"
      >
        <div className="modal__head">
          <h2 id="modal-title">{title}</h2>
          <button className="icon-button" aria-label="Close dialog" onClick={onClose}>
            <Icon name="close" />
          </button>
        </div>
        {children}
      </section>
    </div>
  );
}

export function PageHeading({ eyebrow, title, description, action }) {
  return (
    <div className="page-heading">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="page-heading__description">{description}</p>}
      </div>
      {action}
    </div>
  );
}
