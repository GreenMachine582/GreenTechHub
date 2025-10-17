import { select, on, onclick } from "../helpers.js";

(function () {
  'use strict';

  // ------------ Helpers ------------
  const debounce = (fn, wait = 250) => {
    let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), wait); };
  };

  function el(tag, attrs = {}, children = []) {
    const e = document.createElement(tag);
    Object.entries(attrs || {}).forEach(([k, v]) => {
      if (k === 'class') e.className = v;
      else if (k === 'dataset') Object.assign(e.dataset, v || {});
      else if (k.toLowerCase().startsWith('on') && typeof v === 'function') {
        e.addEventListener(k.slice(2).toLowerCase(), v);
      } else if (v != null) {
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
    eq: '==', neq: '!=', lt: '<', lte: '<=', gt: '>', gte: '>=',
    in: 'in', isnull: 'is_null', notnull: 'is_not_null',
    istrue: '==', isfalse: '==', contains: 'ilike', startswith: 'ilike', endswith: 'ilike',
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

      if (op === 'isnull' || op === 'notnull') return { field, op: OP_MAP[op] };
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

  // ------------ UI helpers (operators/inputs/toggles) ------------
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
      wrap.append(i1, el('span', { class: 'muted' }, '…'), i2);
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
      class: 'btn-group btn-group-sm qb-combinator', role: 'group', title: 'Combine rules'
    });

    const options = [
      { val: 'AND', label: 'AND', icon: 'fa-solid fa-link' },
      { val: 'OR',  label: 'OR',  icon: 'fa-solid fa-code-branch' }
    ];

    const inputs = [], labels = [];

    const syncPressed = () => {
      labels.forEach((lab, i) => lab.setAttribute('aria-pressed', String(inputs[i].checked)));
    };

    options.forEach(({ val, label, icon }) => {
      const input = el('input', {
        class: 'btn-check', type: 'radio', name: idBase, id: `${idBase}-${val}`, autocomplete: 'off'
      });
      input.checked = String(current).toUpperCase() === val;

      const btn = el('label', {
        class: 'btn btn-outline-primary',
        for: `${idBase}-${val}`,
        title: label,
        'aria-pressed': String(input.checked)
      }, [ el('i', { class: icon }) ]);

      input.addEventListener('change', () => { syncPressed(); onChange?.(val); });

      inputs.push(input); labels.push(btn);
      wrap.append(input, btn);
    });

    return wrap;
  }

  function segmentedToggle(opts, current, onChange) {
    const idBase = 'qb-seg-' + Math.random().toString(36).slice(2);
    const wrap = el('div', { class: 'btn-group btn-group-sm qb-seg', role: 'group' });
    const inputs = [], labels = [];

    const sync = () => {
      labels.forEach((lab, i) => {
        const on = inputs[i].checked;
        lab.classList.toggle('active', on);
        lab.setAttribute('aria-pressed', String(on));
      });
    };

    opts.forEach(({ id, label, icon }) => {
      const input = el('input', {
        class: 'btn-check', type: 'radio', name: idBase, id: `${idBase}-${id}`, autocomplete: 'off'
      });
      input.checked = (current === id);
      const lab = el('label', {
        class: 'btn btn-outline-secondary',
        for: `${idBase}-${id}`,
        'aria-pressed': String(input.checked),
        title: label,
      }, [ icon ? el('i', { class: icon }) : null, el('span', {}, label) ]);

      input.addEventListener('change', () => { if (input.checked) { sync(); onChange?.(id); } });

      inputs.push(input); labels.push(lab);
      wrap.append(input, lab);
    });

    sync();
    return wrap;
  }

  function booleanOpToggle(current = 'istrue', onChange) {
    return segmentedToggle([
      { id: 'istrue',  label: 'True',     icon: 'fa-solid fa-toggle-on' },
      { id: 'isfalse', label: 'False',    icon: 'fa-solid fa-toggle-off' },
      { id: 'isnull',  label: 'Null',     icon: 'fa-regular fa-circle-dot' },
      { id: 'notnull', label: 'Not null', icon: 'fa-regular fa-circle' }
    ], current, onChange);
  }

  function collapseExpandButton(qb) {
    const btn = el('button', {
      type: 'button',
      class: 'btn btn-sm btn-outline-secondary',
      title: qb.collapsed ? 'Expand filters' : 'Collapse filters',
      'aria-expanded': String(!qb.collapsed),
    }, [ el('i', { class: qb.collapsed ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-up' }) ]);

    onclick(btn, () => {
      qb.collapsed = !qb.collapsed;
      qb.applyCollapse?.();
    });

    qb._collapseBtn = btn;
    return btn;
  }

  // ---------- Buttons ----------
  function iconButton(iconClass, label, onClick, { variant = 'secondary', outline = true } = {}) {
    const btnClass = outline ? `btn btn-sm btn-outline-${variant}` : `btn btn-sm btn-${variant}`;
    const btn = el('button', {
      type: 'button',
      class: btnClass,
      title: label,
    }, [
      el('i', { class: iconClass }),
      el('span', { class: 'visually-hidden' }, ' ' + label),
    ]);
    onclick(btn, () => {
      btn.blur();
      onClick?.();
    });
    return btn;
  }

  function asyncIconButton(iconClass, label, onClick, { variant = 'primary', outline = false } = {}) {
    const btn = iconButton(iconClass, label, null, { variant, outline });
    onclick(btn, async () => {
      btn.blur();
      const icon = btn.querySelector('i');
      const orig = icon?.getAttribute('class');
      try {
        const p = onClick?.();
        if (p && typeof p.then === 'function') {
          btn.disabled = true;
          if (icon) icon.setAttribute('class', 'fa-solid fa-spinner fa-spin');
          await p;
        }
      } finally {
        btn.disabled = false;
        if (icon && orig) icon.setAttribute('class', orig);
      }
    });
    return btn;
  }

  // ------------ QueryBuilder ------------
  function QueryBuilder(root, options = {}) {
    this.root = root;
    this.fields = options.fields || [];
    this.mode = options.mode || 'AND';
    this.compact = !!options.compact;
    this.collapsed = !!options.collapsed;
    this.onChange = options.onChange || function () {};
    this.onSearch = typeof options.onSearch === 'function' ? options.onSearch : null;
    this.hidden = options.hiddenInput || null; // hidden input to write JSON into
    this.state = { combinator: this.mode, rules: [] };

    this._debouncedSearch = debounce(() => this.search(), options.searchDebounceMs ?? 250);
    this.scheduleSearch = () => this._debouncedSearch();

    this.render();
  }

  Object.assign(QueryBuilder.prototype, {

    _computePayload() {
      const qbTree = this.getRules();
      const saf = qbTreeToSafPayload(qbTree);
      const json = saf ? JSON.stringify(saf) : '';
      return { qbTree, saf, json };
    },

    _ensureExpanded() {
      if (this.collapsed) {
        this.collapsed = false;
        this.applyCollapse();
      }
    },

    fieldByName(name) {
      return this.fields.find(f => f.name === name);
    },

    // ------------ Rendering ------------
    render() {
      this.root.innerHTML = '';
      this.root.classList.add('qb');
      if (this.compact) this.root.classList.add('qb-compact');

      const header = el('div', { class: 'qb-header' }, [
        el('strong', {}, 'Filters'),
        (() => combinatorToggle(this.state.combinator, (val) => {
          this.state.combinator = val; this.emit();
        }))(),
        el('div', { class: 'qb-actions btn-group btn-group-sm' }, [
          collapseExpandButton(this),
          iconButton('fa-solid fa-plus', 'Add rule',  () => this.addRule(), { variant: 'success',
            outline: false }),
          iconButton('fa-solid fa-layer-group', 'Add group', () => this.addGroup(), { variant: 'success',
            outline: false }),
          iconButton('fa-solid fa-eraser', 'Clear all', () => this.clear(), { variant: 'warning',
            outline: false }),
          asyncIconButton('fa-solid fa-magnifying-glass', 'Search', () => this.search(), { variant: 'primary',
            outline: false }),
        ]),
      ]);
      this.root.appendChild(header);

      const children = el('div', { class: 'qb-children qb-root-children' });
      this.rulesContainer = children;
      this.root.appendChild(children);

      const rootGroupNode = { rules: this.state.rules };
      this.state.rules.forEach((r, idx) => this.renderNode(r, children, idx, rootGroupNode));

      this.applyCollapse();
      this.emit();
    },

    renderNode(node, parentEl, index, parentGroupNode) {
      if (node.type === 'group') return this.renderGroup(node, parentEl, index, parentGroupNode);
      return this.renderRule(node, parentEl, index, parentGroupNode);
    },

    renderGroup(groupNode, parentEl, index, parentGroupNode) {
      const wrap = el('div', { class: 'qb-group' });
      const header = el('div', { class: 'qb-header' }, [
        el('span', { class: 'muted' }, 'Group'),
        (() => combinatorToggle(groupNode.combinator || 'AND', (val) => { groupNode.combinator = val; this.emit(); this.scheduleSearch(); }))(),
        el('div', { class: 'qb-actions btn-group btn-group-sm' }, [
          iconButton('fa-solid fa-plus',        'Add rule',
            () => this.addRule(groupNode), { variant: 'success', outline: false }),
          iconButton('fa-solid fa-layer-group', 'Add group',
            () => this.addGroup(groupNode), { variant: 'success', outline: false }),
          iconButton('fa-solid fa-trash',       'Remove group',
            () => this.removeNode(index, parentGroupNode),
            { variant: 'danger', outline: false }),
        ]),
      ]);
      wrap.appendChild(header);

      const children = el('div', { class: 'qb-children' });
      wrap.appendChild(children);

      groupNode.rules = groupNode.rules || [];
      groupNode.rules.forEach((child, idx) => this.renderNode(child, children, idx, groupNode));

      parentEl.appendChild(el('div', { class: 'qb-child qb-group-node' }, wrap));
    },

    renderRule(rule, parentEl, index, parentGroupNode) {
      const fieldSel = el('select');
      this.fields.forEach(f => fieldSel.appendChild(el('option', { value: f.name }, f.label || f.name)));
      fieldSel.value = rule.field || (this.fields[0] && this.fields[0].name);
      const field = this.fieldByName(fieldSel.value);

      const opSel = el('select');
      buildOperatorOptions(field.type).forEach(op => opSel.appendChild(el('option', { value: op.id }, op.label)));
      opSel.value = rule.op || opSel.options[0].value;

      let valueInput = inputFor(field, opSel.value, rule.value);

      // Containers
      const opWrap = el('div', { class: 'qb-op-wrap' }, [opSel]);
      const valWrap = el('div', { class: 'qb-val-wrap' }, [valueInput || el('span', { class: 'text-muted' }, '—')]);

      const row = el('div', { class: 'qb-row' }, [
        fieldSel, opWrap, valWrap,
        el('div', { class: 'qb-actions btn-group btn-group-sm' }, [
          iconButton('fa-solid fa-xmark', 'Remove rule',
            () => this.removeNode(index, parentGroupNode), { variant: 'danger', outline: false }
          ),
        ]),
      ]);

      const setValuePlaceholder = () => {
        valWrap.innerHTML = '';
        valWrap.appendChild(el('span', { class: 'text-muted' }, '—'));
      };

      const mountValueInput = (f, op, v) => {
        valWrap.innerHTML = '';
        valueInput = inputFor(f, op, v);
        if (valueInput) {
          valWrap.appendChild(valueInput);
          on('change', valueInput, () => {
            const f2 = this.fieldByName(fieldSel.value);
            rule.value = valueFromInput(f2, rule.op, valueInput);
            this.emit(); this.scheduleSearch();
          });
        } else {
          setValuePlaceholder();
        }
      };

      // --- helpers to (re)mount op + value UIs per field/op ---
      const mountBooleanUI = (currentOp) => {
        // hide the select, mount segmented toggle
        opSel.classList.add('d-none');
        select('.qb-seg', false, opWrap)?.remove();
        const seg = booleanOpToggle(currentOp || 'istrue', (newOp) => {
          opSel.value = newOp;
          rule.op = newOp;
          // boolean ops carry their own value (istrue/isfalse) or no value (isnull/notnull)
          setValuePlaceholder(); // always placeholder for boolean
          this.emit(); this.scheduleSearch();
        });
        opWrap.appendChild(seg);
        setValuePlaceholder(); // no explicit value for boolean
      };

      const mountDefaultOpUI = (f) => {
        // show the select and remove segmented toggle if present
        opSel.classList.remove('d-none');
        select('.qb-seg', false, opWrap)?.remove();
        // rebuild options for the new field type
        opSel.innerHTML = '';
        buildOperatorOptions(f.type).forEach(op => opSel.appendChild(el('option', { value: op.id }, op.label)));
        // preserve previous op if compatible, else pick first
        const first = buildOperatorOptions(f.type)[0]?.id || 'eq';
        opSel.value = (rule.op && [...opSel.options].some(o => o.value === rule.op)) ? rule.op : first;
        mountValueInput(f, opSel.value, null);
      };

      // Initial mount based on field type
      if (field.type === 'boolean') {
        mountBooleanUI(rule.op || 'istrue');
      } else {
        mountDefaultOpUI(field);
      }

      // Listeners
      on('change', fieldSel, () => {
        const f = this.fieldByName(fieldSel.value);
        rule.field = f.name;
        if (f.type === 'boolean') {
          const nextOp = ['istrue','isfalse','isnull','notnull'].includes(rule.op) ? rule.op : 'istrue';
          rule.op = nextOp; rule.value = null;
          mountBooleanUI(nextOp);
        } else {
          mountDefaultOpUI(f);
          rule.op = opSel.value;
          rule.value = valueFromInput(f, rule.op, valueInput);
        }
        this.emit(); this.scheduleSearch();
      });

      // op change (for non-boolean)
      on('change', opSel, () => {
        const f = this.fieldByName(fieldSel.value);
        rule.op = opSel.value;

        // If this op doesn't need a value, show placeholder; else mount input
        const needsValue = !['isnull','notnull','istrue','isfalse'].includes(rule.op);
        if (f.type === 'boolean') {
          // Shouldn't happen (boolean uses segmented toggle), but keep consistent
          setValuePlaceholder();
          rule.value = null;
        } else if (needsValue) {
          mountValueInput(f, rule.op, null);
          rule.value = valueFromInput(f, rule.op, valueInput);
        } else {
          setValuePlaceholder();
          rule.value = null;
        }
        this.emit(); this.scheduleSearch();
      });

      // Init rule values
      rule.field = fieldSel.value;
      rule.op = (field.type === 'boolean') ? (rule.op || 'istrue') : (opSel.value || 'eq');
      if (field.type === 'boolean' || ['isnull','notnull','istrue','isfalse'].includes(rule.op)) {
        rule.value = null;
      } else {
        rule.value = valueFromInput(field, rule.op, valueInput);
      }

      parentEl.appendChild(el('div', { class: 'qb-child qb-rule-node' }, row));
    },

    // --- mutations ---
    addRule(groupNode) {
      this._ensureExpanded?.();
      const target = groupNode ? (groupNode.rules = groupNode.rules || [], groupNode.rules) : this.state.rules;
      target.push({type: 'rule', field: (this.fields[0] && this.fields[0].name) || null, op: null, value: null});
      this.render();
    },

    addGroup(groupNode) {
      this._ensureExpanded?.();
      const target = groupNode ? (groupNode.rules = groupNode.rules || [], groupNode.rules) : this.state.rules;
      target.push({ type: 'group', combinator: 'AND', rules: [] });
      this.render();
    },

    removeNode(index, node) {
      this.removeAtArray((node ? node.rules : this.state.rules), index);
      this.scheduleSearch();
    },

    removeAtArray(arr, idx) {
      if (!Array.isArray(arr)) return;
      arr.splice(idx, 1);
      this.render();
    },

    clear() {
      this.state = { combinator: this.mode, rules: [] };
      this.render();
      this.scheduleSearch();
    },

    getRules() {
      const clean = (node) => {
        if (!node) return null;
        if (node.type === 'rule' || (node.field && !node.type)) {
          const n = { type: 'rule', field: node.field, op: node.op, value: node.value };
          const needsValue = !['isnull', 'notnull', 'istrue', 'isfalse'].includes(n.op);
          if (!n.field || !n.op) return null;
          if (needsValue && (n.value == null || (Array.isArray(n.value) && n.value.length === 0))) return null;
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
    },

    setRules(tree) {
      if (!tree || typeof tree !== 'object') return;
      if (tree.type === 'group') {
        this.state.combinator = tree.combinator || 'AND';
        this.state.rules = tree.rules || [];
      } else {
        this.state.rules = Array.isArray(tree.rules) ? tree.rules : [];
      }
      this.render();
    },

    emit() {
      const { qbTree, saf, json } = this._computePayload();
      if (this.hidden) {
        this.hidden.value = json;
        this.hidden.setAttribute('value', json);
      }
      this.onChange(qbTree, saf, json);
    },

    applyCollapse() {
      const collapsed = !!this.collapsed;
      this.root.classList.toggle('qb-collapsed', collapsed);

      // Toggle visibility/ARIA on the children container
      if (this.rulesContainer) this.rulesContainer.setAttribute('aria-hidden', String(collapsed));

      // Update the button icon + title + aria-expanded
      if (this._collapseBtn) {
        const icon = this._collapseBtn.querySelector('i');
        if (icon) icon.className = collapsed ? 'fa-solid fa-chevron-down' : 'fa-solid fa-chevron-up';
        this._collapseBtn.setAttribute('data-tip', collapsed ? 'Expand filters' : 'Collapse filters');
        this._collapseBtn.setAttribute('aria-expanded', String(!collapsed));
      }
    },

    search() {
      this.emit();
      const payload = this._computePayload();
      if (this.onSearch) return this.onSearch(payload, this);
      this.root.dispatchEvent(new CustomEvent('qb:search', { bubbles: true, detail: { ...payload, qb: this } }));
    },
  });

  // ------------ Auto-init ------------
  function autoInit() {
    select('[data-qb]:not([data-qb-enhanced])', true).forEach(node => {
      const configId = node.getAttribute('data-config-id');
      const hiddenSelector = node.getAttribute('data-hidden');
      const compact = node.getAttribute('data-compact') === 'true';
      const initial = node.getAttribute('data-initial');
      const collapsed = node.getAttribute('data-collapsed') === 'true';
      const fields = window.__QB_CONFIGS__ && window.__QB_CONFIGS__[configId];
      if (!fields) return;

      const hidden = hiddenSelector ? select(hiddenSelector) : null;
      const qb = new QueryBuilder(node, { fields, compact, collapsed, hiddenInput: hidden });

      if (initial) { try { qb.setRules(JSON.parse(initial)); } catch { /* ignore */ } }

      node.__qb = qb; node.setAttribute('data-qb-enhanced', '1');
    });
  }

  if (!window.__QB_CONFIGS__) window.__QB_CONFIGS__ = {};
  window.QueryBuilder = QueryBuilder;

  if (document.readyState === 'loading') {
    on('DOMContentLoaded', document, autoInit);
  } else {
    autoInit();
  }
})();
