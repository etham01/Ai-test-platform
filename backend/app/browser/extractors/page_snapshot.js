(() => {
  const clean = (value) => (value || "").replace(/\s+/g, " ").trim();
  const clipped = (value, max) => clean(value).slice(0, max);

  const isVisible = (el) => {
    if (!el) return false;
    const rect = el.getBoundingClientRect();
    const style = window.getComputedStyle(el);
    return (
      rect.width > 0 &&
      rect.height > 0 &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.opacity !== "0"
    );
  };

  const labelFor = (el) => {
    if (el.labels && el.labels.length) return clipped(el.labels[0].innerText, 512);
    const id = el.getAttribute("id");
    if (id) {
      const node = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (node) return clipped(node.innerText, 512);
    }
    const parentLabel = el.closest("label");
    return parentLabel ? clipped(parentLabel.innerText, 512) : "";
  };

  const implicitRole = (tag, el) => {
    if (el.getAttribute("role")) return el.getAttribute("role");
    if (tag === "a") return "link";
    if (tag === "button") return "button";
    if (tag === "select") return "combobox";
    if (tag === "textarea") return "textbox";
    if (tag === "form") return "form";
    if (tag === "input") {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      if (["submit", "button", "reset"].includes(type)) return "button";
      if (type === "checkbox") return "checkbox";
      if (type === "radio") return "radio";
      return "textbox";
    }
    return null;
  };

  const accessibleName = (el, tag) => {
    const explicit = el.getAttribute("aria-label") || el.getAttribute("title");
    if (explicit) return clipped(explicit, 512);
    const label = labelFor(el);
    if (label) return label;
    const placeholder = el.getAttribute("placeholder");
    if (placeholder) return clipped(placeholder, 512);
    if (tag === "button" || tag === "a") return clipped(el.innerText, 512);
    return "";
  };

  const elementType = (tag, el) => {
    if (tag === "a") return "link";
    if (tag === "button") return "button";
    if (tag === "input") {
      const type = (el.getAttribute("type") || "text").toLowerCase();
      return ["submit", "button", "reset"].includes(type) ? "button" : "input";
    }
    if (["select", "textarea", "form"].includes(tag)) return tag;
    return "other";
  };

  const isSensitive = (tag, el) => {
    if (tag !== "input" && tag !== "textarea") return false;
    const type = (el.getAttribute("type") || "text").toLowerCase();
    if (["password", "email", "tel"].includes(type)) return true;
    const autocomplete = (el.getAttribute("autocomplete") || "").toLowerCase();
    if (autocomplete.startsWith("cc-")) return true;
    const haystack = [
      el.getAttribute("name") || "",
      el.getAttribute("id") || "",
      el.getAttribute("placeholder") || "",
      labelFor(el),
    ]
      .join(" ")
      .toLowerCase();
    return /password|passwd|token|secret|card|cvv|email|phone|手机号|密码|邮箱/.test(haystack);
  };

  const selectorCandidates = (el, tag, role, name, label, placeholder, text) => {
    const candidates = {};
    if (role && name) candidates.role = { role, name };
    if (label) candidates.label = label;
    if (placeholder) candidates.placeholder = placeholder;
    if (text && (tag === "button" || tag === "a")) candidates.text = text;
    const id = el.getAttribute("id");
    const testId = el.getAttribute("data-testid");
    const fieldName = el.getAttribute("name");
    if (id) candidates.css = `#${CSS.escape(id)}`;
    else if (testId) candidates.test_id = testId;
    else if (fieldName) candidates.css = `${tag}[name="${CSS.escape(fieldName)}"]`;
    return Object.keys(candidates).length ? candidates : null;
  };

  const elements = [];
  const seen = new Set();
  const nodes = document.querySelectorAll(
    "a[href], button, input, select, textarea, form, [role], [aria-label], [data-testid]",
  );

  for (const el of nodes) {
    if (elements.length >= 80) break;
    if (!isVisible(el)) continue;
    const tag = el.tagName.toLowerCase();
    const type = elementType(tag, el);
    const role = implicitRole(tag, el);
    const name = accessibleName(el, tag);
    const label = labelFor(el);
    const placeholder = clipped(el.getAttribute("placeholder"), 512);
    const text = elementType(tag, el) === "link" || tag === "button"
      ? clipped(el.innerText, 1024)
      : "";
    const elementId = clipped(el.getAttribute("id"), 256);
    const fieldName = clipped(el.getAttribute("name"), 256);
    const inputType = tag === "input" ? clipped(el.getAttribute("type") || "text", 64) : null;
    const href = tag === "a" ? (el.href || "").slice(0, 2048) : null;
    const key = [tag, elementId, fieldName, role, name, placeholder, text].join("|");
    if (seen.has(key)) continue;
    seen.add(key);

    elements.push({
      element_type: type,
      tag,
      role,
      accessible_name: name || null,
      label: label || null,
      placeholder: placeholder || null,
      text: text || null,
      element_id: elementId || null,
      name: fieldName || null,
      input_type: inputType,
      href,
      selector_candidates: selectorCandidates(el, tag, role, name, label, placeholder, text),
      is_sensitive: isSensitive(tag, el),
      attributes: {
        aria_label: clipped(el.getAttribute("aria-label"), 512) || null,
        title: clipped(el.getAttribute("title"), 512) || null,
        test_id: clipped(el.getAttribute("data-testid"), 256) || null,
        autocomplete: clipped(el.getAttribute("autocomplete"), 128) || null,
      },
    });
  }

  const links = [];
  for (const anchor of document.querySelectorAll("a[href]")) {
    if (links.length >= 100) break;
    if (!isVisible(anchor)) continue;
    const href = (anchor.href || "").trim();
    if (!href) continue;
    links.push({ href, text: clipped(anchor.innerText, 300) });
  }

  const forms = [];
  for (const form of document.querySelectorAll("form")) {
    if (forms.length >= 20) break;
    const fields = [...form.querySelectorAll("input, select, textarea, button")]
      .slice(0, 30)
      .map((field) => ({
        tag: field.tagName.toLowerCase(),
        type: (field.getAttribute("type") || "").toLowerCase() || null,
        name: field.getAttribute("name") || null,
        label: labelFor(field) || null,
        placeholder: clipped(field.getAttribute("placeholder"), 256) || null,
      }));
    forms.push({
      action: (form.action || form.getAttribute("action") || "").slice(0, 2048),
      method: (form.method || "get").toLowerCase(),
      fields,
    });
  }

  const bodyText = clipped(document.body ? document.body.innerText : "", 8000);
  const clone = document.documentElement.cloneNode(true);
  clone.querySelectorAll("script, style, noscript, svg").forEach((node) => node.remove());
  clone.querySelectorAll("input, textarea").forEach((node) => {
    node.removeAttribute("value");
    node.setAttribute("value", "");
    if (node.tagName === "TEXTAREA") node.textContent = "";
  });
  const dom = clone.outerHTML.slice(0, 200000);

  return {
    title: document.title || "",
    bodyText,
    dom,
    links,
    forms,
    elements,
    url: window.location.href,
  };
})()
