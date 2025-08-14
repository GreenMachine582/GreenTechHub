(function () {
  'use strict';

  /** Create a DOM element */
  function el(tag, attrs = {}, children = []) {
    const e = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'class') e.className = v;
      else if (k === 'dataset') Object.assign(e.dataset, v);
      else if (k.toLowerCase().startsWith('on') && typeof v === 'function') {
        e.addEventListener(k.slice(2).toLowerCase(), v);
      } else {
        e.setAttribute(k, v);
      }
    });
    (Array.isArray(children) ? children : [children]).forEach(c => {
      if (c == null) return;
      if (typeof c === 'string') e.appendChild(document.createTextNode(c));
      else e.appendChild(c);
    });
    return e;
  }

  // ---------- SQLAlchemy Filters conversion ----------
  const OP_MAP = Object.freeze({
    eq: '==',
    neq: '!=',
    lt: '<',
    lte: '<=',
    gt: '>',
    gte: '>=',
    in: 'in',
    isnull: 'is_null',
    notnull: 'is_not_null',
    istrue: '==',
    isfalse: '==',
    contains: 'ilike',
    startswith: 'ilike',
    endswith: 'ilike',
  });

  function likeWrap(op, val) {
    if (val == null) return val;
    if (op === 'contains')   return `%${val}%`;
    if (op === 'startswith') return `${val}%`;
    if (op === 'endswith')   return `%${val}`;
    return val;
  }

  function qbToSaf(node) {
    if (!node) return null;

    // Leaf
    if (node.type === 'rule') {
      const { field, op, value } = node;
      if (!field || !op) return null;

      if (op === 'isnull' || op === 'notnull') {
        return { field, op: OP_MAP[op] };
      }
      if (op === 'istrue')  return { field, op: '==', value: true  };
      if (op === 'isfalse') return { field, op: '==', value: false };

      if (op === 'between') {
        const [a, b] = Array.isArray(value) ? value : [null, null];
        const parts = [];
        if (a != null && a !== '') parts.push({ field, op: '>=', value: a });
        if (b != null && b !== '') parts.push({ field, op: '<=', value: b });
        if (!parts.length) return null;
        return parts.length === 1 ? parts[0] : { and: parts };
      }

      if (op === 'contains' || op === 'startswith' || op === 'endswith') {
        const v = likeWrap(op, value);
        if (v == null || v === '') return null;
        return { field, op: 'ilike', value: v };
      }

      const mapped = OP_MAP[op] || '==';
      if (mapped === 'in') {
        const arr = Array.isArray(value) ? value : (value == null ? [] : [value]);
        if (!arr.length) return null;
        return { field, op: 'in', value: arr };
      }
      return { field, op: mapped, value };
    }

    // Group
    const combinator = (node.combinator || 'AND').toLowerCase(); // 'and' | 'or'
    const children = (node.rules || []).map(qbToSaf).filter(Boolean);
    if (!children.length) return null;
    return { [combinator]: children };
  }

  function qbTreeToSafPayload(qbTree) {
    if (!qbTree || !qbTree.rules) return null;
    return qbToSaf(qbTree) || null;
  }

  // ---------- UI: operators & inputs ----------
  const OPS_BY_TYPE = Object.freeze({
    string: [
      { id: 'eq', label: 'is' },
      { id: 'neq', label: 'is not' },
      { id: 'contains', label: 'contains' },
      { id: 'startswith', label: 'starts with' },
      { id: 'endswith', label: 'ends with' },
      { id: 'isnull', label: 'is empty' },
      { id: 'notnull', label: 'is not empty' },
      { id: 'in', label: 'in (comma list)' },
    ],
    number: [
      { id: 'eq', label: '=' },
      { id: 'neq', label: '≠' },
      { id: 'lt', label: '<' },
      { id: 'lte', label: '≤' },
      { id: 'gt', label: '>' },
      { id: 'gte', label: '≥' },
      { id: 'in', label: 'in (comma list)' },
      { id: 'isnull', label: 'is null' },
      { id: 'notnull', label: 'is not null' },
    ],
    boolean: [
      { id: 'istrue', label: 'is true' },
      { id: 'isfalse', label: 'is false' },
      { id: 'isnull', label: 'is null' },
      { id: 'notnull', label: 'is not null' },
    ],
    date: [
      { id: 'eq', label: 'on' },
      { id: 'lt', label: 'before' },
      { id: 'gt', label: 'after' },
      { id: 'between', label: 'between' },
      { id: 'isnull', label: 'is null' },
      { id: 'notnull', label: 'is not null' },
    ],
  });

  function buildOperatorOptions(type) {
    return OPS_BY_TYPE[type] || OPS_BY_TYPE.string;
  }

  function inputFor(field, op, value) {
    const type = field.type;
    if (type === 'boolean') {
      const sel = el('select', {}, [
        el('option', { value: '' }, '--'),
        el('option', { value: 'true' }, 'True'),
        el('option', { value: 'false' }, 'False'),
      ]);
      if (value !== undefined && value !== null) sel.value = String(value);
      return sel;
    }
    if (type === 'date' && op === 'between') {
      const wrap = el('div', { class: 'qb-between d-flex align-items-center gap-2' });
      const i1 = el('input', { type: 'date' });
      const i2 = el('input', { type: 'date' });
      if (Array.isArray(value) && value.length === 2) {
        i1.value = value[0] || ''; i2.value = value[1] || '';
      }
      wrap.appendChild(i1);
      wrap.appendChild(el('span', { class: 'muted' }, '…'));
      wrap.appendChild(i2);
      return wrap;
    }
    const attrs = {};
    if (type === 'number') { attrs.type = 'number'; attrs.step = 'any'; }
    else if (type === 'date') attrs.type = 'date';
    else { attrs.type = 'text'; attrs.placeholder = 'value'; }
    const input = el('input', attrs);
    if (value != null && !Array.isArray(value)) input.value = value;
    return input;
  }

  function valueFromInput(field, op, inputNode) {
    if (field.type === 'boolean') {
      const v = inputNode.value;
      if (v === 'true') return true;
      if (v === 'false') return false;
      return null;
    }
    if (field.type === 'date' && op === 'between') {
      const [i1, , i2] = inputNode.childNodes;
      const a = i1.value || null;
      const b = i2.value || null;
      if (!a && !b) return null;
      return [a, b];
    }
    const raw = inputNode.value?.trim();
    if (!raw && ['isnull', 'notnull'].includes(op)) return null;
    if (!raw) return null;
    if (op === 'in') {
      return raw.split(',').map(s => s.trim()).filter(Boolean);
    }
    if (field.type === 'number') {
      const n = Number(raw);
      return Number.isFinite(n) ? n : null;
    }
    return raw;
  }

  function combinatorToggle(current = 'AND', onChange) {
    const idBase = 'qb-comb-' + Math.random().toString(36).slice(2);

    const wrap = el('div', {
      class: 'btn-group btn-group-sm qb-combinator',
      role: 'group',
      'aria-label': 'Combine rules'
    });

    const options = [
      { val: 'AND', label: 'AND', icon: 'fa-solid fa-link' },
      { val: 'OR',  label: 'OR',  icon: 'fa-solid fa-code-branch' }
    ];

    const inputs = [];
    const labels = [];

    const syncPressed = () => {
      labels.forEach((lab, i) => {
        lab.setAttribute('aria-pressed', String(inputs[i].checked));
      });
    };

    options.forEach(({ val, label, icon }) => {
      const input = el('input', {
        class: 'btn-check',
        type: 'radio',
        name: idBase,
        id: `${idBase}-${val}`,
        autocomplete: 'off'
      });
      input.checked = String(current).toUpperCase() === val;

      const btn = el('label', {
        class: 'btn btn-outline-primary',
        for: `${idBase}-${val}`,
        title: label,
        'data-bs-toggle': 'tooltip',
        'data-bs-placement': 'top',
        'aria-pressed': String(input.checked)
      }, [
        el('i', { class: icon })
      ]);

      input.addEventListener('change', () => {
        syncPressed();
        onChange && onChange(val);
      });

      inputs.push(input);
      labels.push(btn);
      wrap.appendChild(input);
      wrap.appendChild(btn);
    });

    return wrap;
  }

  // ---------- Bootstrap tooltips ----------
  function disposeBSTooltips(root) {
    if (!window.bootstrap || !bootstrap.Tooltip) return;
    root.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(elm => {
      const inst = bootstrap.Tooltip.getInstance(elm);
      if (inst) inst.dispose();
    });
  }
  function initBSTooltips(root) {
    if (!window.bootstrap || !bootstrap.Tooltip) return;
    root.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(elm => {
      new bootstrap.Tooltip(elm, { trigger: 'hover', container: 'body', delay: { show: 150, hide: 50 } });
    });
  }

  // ---------- Buttons ----------
  function iconButton(iconClass, label, onClick, { variant = 'secondary', outline = true } = {}) {
    const btnClass = outline ? `btn btn-sm btn-outline-${variant}` : `btn btn-sm btn-${variant}`;
    const btn = el('button', {
      type: 'button',
      class: btnClass,
      title: label,
      'aria-label': label,
      'data-bs-toggle': 'tooltip',
      'data-bs-placement': 'top',
    }, [
      el('i', { class: iconClass }),
      el('span', { class: 'visually-hidden' }, ' ' + label),
    ]);
    btn.addEventListener('click', (ev) => {
      const inst = (window.bootstrap && bootstrap.Tooltip) ? bootstrap.Tooltip.getInstance(btn) : null;
      if (inst) inst.hide();
      btn.blur();
      onClick && onClick(ev);
    });
    return btn;
  }

  // ---------- QueryBuilder ----------
  function QueryBuilder(root, options) {
    this.root = root;
    this.fields = options.fields || [];
    this.mode = options.mode || 'AND';
    this.compact = !!options.compact;
    this.onChange = options.onChange || function () {};
    this.hidden = options.hiddenInput || null; // hidden input to write JSON into
    this.state = { combinator: this.mode, rules: [] };
    this.render();
  }

  QueryBuilder.prototype.fieldByName = function (name) {
    return this.fields.find(f => f.name === name);
  };

  QueryBuilder.prototype.render = function () {
    disposeBSTooltips(this.root);
    this.root.innerHTML = '';
    this.root.classList.add('qb');
    if (this.compact) this.root.classList.add('qb-compact');

    const header = el('div', { class: 'qb-header' }, [
      el('strong', {}, 'Filters'),
      ( () => {
        const node = combinatorToggle(this.state.combinator, (val) => {
          this.state.combinator = val;
          this.emit();
        });
        return node;
      })(),
      el('div', { class: 'qb-actions btn-group btn-group-sm' }, [
        iconButton('fa-solid fa-plus', 'Add rule',  () => this.addRule(), { variant: 'success', outline: false }),
        iconButton('fa-solid fa-layer-group', 'Add group', () => this.addGroup(), { variant: 'success', outline: false }),
        iconButton('fa-solid fa-eraser', 'Clear all', () => this.clear(), { variant: 'warning', outline: false }),
      ]),
    ]);
    this.root.appendChild(header);

    const children = el('div', { class: 'qb-children qb-root-children' });
    this.rulesContainer = children;
    this.root.appendChild(children);

    const rootGroupNode = { rules: this.state.rules };
    this.state.rules.forEach((r, idx) => this.renderNode(r, children, idx, rootGroupNode));

    this.emit();
    initBSTooltips(this.root);
  };

  QueryBuilder.prototype.renderNode = function (node, parentEl, index, parentGroupNode) {
    if (node.type === 'group') return this.renderGroup(node, parentEl, index, parentGroupNode);
    return this.renderRule(node, parentEl, index, parentGroupNode);
  };

  QueryBuilder.prototype.renderGroup = function (groupNode, parentEl, index, parentGroupNode) {
    const wrap = el('div', { class: 'qb-group' });
    const header = el('div', { class: 'qb-header' }, [
      el('span', { class: 'muted' }, 'Group'),
      ( () => {
        const node = combinatorToggle(groupNode.combinator || 'AND', (val) => {
          groupNode.combinator = val;
          this.emit();
        });
        return node;
      })(),
      el('div', { class: 'qb-actions btn-group btn-group-sm' }, [
        iconButton('fa-solid fa-plus',        'Add rule',     () => this.addRule(groupNode), { variant: 'success', outline: false }),
        iconButton('fa-solid fa-layer-group', 'Add group',    () => this.addGroup(groupNode), { variant: 'success', outline: false }),
        iconButton('fa-solid fa-trash',       'Remove group', () => this.removeAtArray((parentGroupNode ? parentGroupNode.rules : this.state.rules), index), { variant: 'danger', outline: false }),
      ]),
    ]);
    wrap.appendChild(header);

    const children = el('div', { class: 'qb-children' });
    wrap.appendChild(children);

    groupNode.rules = groupNode.rules || [];
    groupNode.rules.forEach((child, idx) => this.renderNode(child, children, idx, groupNode));

    parentEl.appendChild(el('div', { class: 'qb-child qb-group-node' }, wrap));
  };

  QueryBuilder.prototype.renderRule = function (rule, parentEl, index, parentGroupNode) {
    const fieldSel = el('select');
    this.fields.forEach(f => fieldSel.appendChild(el('option', { value: f.name }, f.label || f.name)));
    fieldSel.value = rule.field || (this.fields[0] && this.fields[0].name);
    const field = this.fieldByName(fieldSel.value);

    const opSel = el('select');
    buildOperatorOptions(field.type).forEach(op => opSel.appendChild(el('option', { value: op.id }, op.label)));
    opSel.value = rule.op || opSel.options[0].value;

    let valueInput = inputFor(field, opSel.value, rule.value);

    const row = el('div', { class: 'qb-row' }, [
      fieldSel,
      opSel,
      valueInput,
      el('div', { class: 'qb-actions btn-group btn-group-sm' }, [
        iconButton('fa-solid fa-xmark', 'Remove rule',
          () => this.removeAtArray((parentGroupNode ? parentGroupNode.rules : this.state.rules), index),
          { variant: 'danger', outline: false }
        ),
      ]),
    ]);

    const attachValueHandler = () => {
      valueInput.addEventListener('change', () => {
        const f = this.fieldByName(fieldSel.value);
        rule.value = valueFromInput(f, rule.op, valueInput);
        this.emit();
      });
    };
    attachValueHandler();

    fieldSel.addEventListener('change', () => {
      const f = this.fieldByName(fieldSel.value);
      opSel.innerHTML = '';
      buildOperatorOptions(f.type).forEach(op => opSel.appendChild(el('option', { value: op.id }, op.label)));
      opSel.value = buildOperatorOptions(f.type)[0].id;

      const newInput = inputFor(f, opSel.value, null);
      row.replaceChild(newInput, valueInput);
      valueInput = newInput;
      attachValueHandler();

      rule.field = f.name;
      rule.op = opSel.value;
      rule.value = valueFromInput(f, rule.op, valueInput);
      this.emit();
    });

    opSel.addEventListener('change', () => {
      const f = this.fieldByName(fieldSel.value);
      const newInput = inputFor(f, opSel.value, null);
      row.replaceChild(newInput, valueInput);
      valueInput = newInput;
      attachValueHandler();

      rule.op = opSel.value;
      rule.value = valueFromInput(f, rule.op, valueInput);
      this.emit();
    });

    // Init rule values
    rule.field = fieldSel.value;
    rule.op = opSel.value;
    rule.value = valueFromInput(field, rule.op, valueInput);

    parentEl.appendChild(el('div', { class: 'qb-child qb-rule-node' }, row));
  };

  QueryBuilder.prototype.addRule = function (groupNode) {
    const target = groupNode ? (groupNode.rules = groupNode.rules || [], groupNode.rules) : this.state.rules;
    target.push({ type: 'rule', field: (this.fields[0] && this.fields[0].name) || null, op: null, value: null });
    this.render();
  };

  QueryBuilder.prototype.addGroup = function (groupNode) {
    const target = groupNode ? (groupNode.rules = groupNode.rules || [], groupNode.rules) : this.state.rules;
    target.push({ type: 'group', combinator: 'AND', rules: [] });
    this.render();
  };

  QueryBuilder.prototype.removeAtArray = function (arr, idx) {
    if (!Array.isArray(arr)) return;
    arr.splice(idx, 1);
    this.render();
  };

  QueryBuilder.prototype.clear = function () {
    this.state = { combinator: this.mode, rules: [] };
    this.render();
  };

  QueryBuilder.prototype.getRules = function () {
    const clean = (node) => {
      if (!node) return null;
      if (node.type === 'rule' || (node.field && !node.type)) {
        const n = { type: 'rule', field: node.field, op: node.op, value: node.value };
        const needsValue = !['isnull', 'notnull', 'istrue', 'isfalse'].includes(n.op);
        if (!n.field || !n.op) return null;
        if (needsValue && (n.value === null || n.value === undefined || (Array.isArray(n.value) && n.value.length === 0))) return null;
        return n;
      }
      if (node.type === 'group' || node.rules) {
        const combinator = node.combinator || 'AND';
        const rules = (node.rules || []).map(clean).filter(Boolean);
        if (!rules.length) return null;
        return { type: 'group', combinator, rules };
      }
      return null;
    };
    const root = clean({ type: 'group', combinator: this.state.combinator, rules: this.state.rules });
    return root || { type: 'group', combinator: this.state.combinator, rules: [] };
  };

  QueryBuilder.prototype.setRules = function (tree) {
    if (!tree || typeof tree !== 'object') return;
    if (tree.type === 'group') {
      this.state.combinator = tree.combinator || 'AND';
      this.state.rules = tree.rules || [];
    } else {
      this.state.rules = Array.isArray(tree.rules) ? tree.rules : [];
    }
    this.render();
  };

  QueryBuilder.prototype.emit = function () {
    const qbTree = this.getRules();
    const saf = qbTreeToSafPayload(qbTree);
    if (this.hidden) {
      const json = saf ? JSON.stringify(saf) : '';
      this.hidden.value = json;                 // property
      this.hidden.setAttribute('value', json);  // attribute (MutationObserver listeners)
    }
    this.onChange(qbTree);
  };

  // ---------- Auto-init ----------
  function autoInit() {
    document.querySelectorAll('[data-qb]:not([data-qb-enhanced])').forEach(node => {
      const configId = node.getAttribute('data-config-id');
      const hiddenSelector = node.getAttribute('data-hidden');
      const compact = node.getAttribute('data-compact') === 'true';
      const initial = node.getAttribute('data-initial');
      const fields = window.__QB_CONFIGS__ && window.__QB_CONFIGS__[configId];
      if (!fields) return;

      const hidden = hiddenSelector ? document.querySelector(hiddenSelector) : null;
      const qb = new QueryBuilder(node, { fields, compact, hiddenInput: hidden, onChange: () => {} });

      if (initial) {
        try { qb.setRules(JSON.parse(initial)); } catch { /* ignore */ }
      }

      node.__qb = qb;
      node.setAttribute('data-qb-enhanced', '1');
    });
  }

  if (!window.__QB_CONFIGS__) window.__QB_CONFIGS__ = {};
  window.QueryBuilder = QueryBuilder;

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', autoInit);
  } else {
    autoInit();
  }
})();
