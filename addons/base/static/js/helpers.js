/**
 * Select element(s) by CSS selector OR accept a Node / NodeList directly.
 * When `all=true`, returns an array (never NodeList).
 */
export const select = (target, all = false, scope = document) => {
  // CSS selector
  if (typeof target === 'string') {
    const sel = target.trim();
    return all
      ? [...(scope || document).querySelectorAll(sel)]
      : (scope || document).querySelector(sel);
  }

  // Single node-like (Element, Document, Window)
  if (target === window || target === document || (target && target.nodeType === 1)) {
    return target;
  }

  // NodeList / array of nodes
  if (target && (target instanceof NodeList || Array.isArray(target))) {
    return all ? [...target] : target[0] || null;
  }

  return all ? [] : null;
};

/**
 * Event listener helper.
 * - `el` can be CSS selector, Element, Document, Window, or NodeList.
 * - When `all=true`, binds to all matched elements (or each node in a NodeList).
 */
export const on = (type, el, listener, all = false, options) => {
  if (all) {
    const nodes =
      typeof el === 'string'
        ? select(el, true)
        : (el && (el instanceof NodeList || Array.isArray(el))) ? [...el] : [el];

    nodes.forEach((n) => n?.addEventListener?.(type, listener, options));
    return;
  }
  const node = typeof el === 'string' ? select(el) : el;
  node?.addEventListener?.(type, listener, options);
};

/**
 * Easy on click event listener
 */
export const onclick = (el, listener) => {
  el.addEventListener('click', listener)
}

/**
 * Easy on scroll event listener
 */
export const onscroll = (el, listener) => {
  el.addEventListener('scroll', listener)
}
