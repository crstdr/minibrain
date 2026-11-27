// Grid geometry. Pure: no DOM, no state.
//
// A box is a rectangle in grid cells {id, x, y, w, h, g}: top-left corner, size
// including the free gap kept right of and below it, and its group id (or null).
// Sizes and gaps are whole cells, so "is this spot free" is integer arithmetic.

export const CHIP_W = 232, CHIP_H = 54, GAP = 8, PAD = 12;
// One cell is a quarter of a chip column (240 px) and half a chip row (62 px).
export const CW = 60, CH = 31;
// Free space kept between boxes, chosen so that box plus gap is whole cells:
// width 240c + 16 + 44 = 60(4c + 1), height 62r + 16 + 77 = 31(2r + 3). The 77 px
// below a box hold the title of whatever sits under it.
export const GAPX = 44, GAPY = 77;

export function colsFor(n) { return n <= 4 ? 1 : n <= 13 ? 2 : n <= 27 ? 3 : 4; }

// Pixel size (w, h) and cell size including the gap (wc, hc) of a box with n chips.
// A box without chips is emptyCells wide, wide enough for its own title.
export function boxSize(n, cols, emptyCells) {
  if (!n) return { w: emptyCells * CW - GAPX, h: 4 * CH - GAPY, wc: emptyCells, hc: 4, cols: 1 };
  const rows = Math.ceil(n / cols);
  return { w: 240 * cols + 16, h: 62 * rows + 16, wc: 4 * cols + 1, hc: 2 * rows + 3, cols: cols };
}

export function hit(a, b) {
  return a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
}

function overlap(a, b) {   // shared area in cells
  const w = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x), h = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
  return w > 0 && h > 0 ? w * h : 0;
}

export function bounds(list) {
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const b of list) {
    x0 = Math.min(x0, b.x); y0 = Math.min(y0, b.y);
    x1 = Math.max(x1, b.x + b.w); y1 = Math.max(y1, b.y + b.h);
  }
  return list.length ? { x0, y0, x1, y1 } : { x0: 0, y0: 0, x1: 0, y1: 0 };
}

// The space a group claims: its members' bounding rectangle plus room for the frame
// and, above it, the group's title. No outside box or other group may touch it.
export function frameRect(members) {
  const b = bounds(members);
  return { x: b.x0 - 1, y: b.y0 - 3, w: b.x1 - b.x0 + 2, h: b.y1 - b.y0 + 4 };
}

// The frame as drawn, in pixels: 30 px outside the members left and right, two cells
// above them (their own titles sit there), 46 px below.
export function framePixels(members) {
  const b = bounds(members);
  const x = b.x0 * CW - 30, y = (b.y0 - 2) * CH;
  return { x: x, y: y, w: b.x1 * CW - 14 - x, h: (b.y1 - 1) * CH - y };
}

// What the moving boxes (one box, or boxes of one group) must not touch.
function obstacles(boxes, moving) {
  const ids = new Set(moving.map(function (b) { return b.id; }));
  const g = moving[0].g || null;
  const siblings = [], groups = new Map();
  let others = [], direct = [];
  boxes.forEach(function (b) {
    if (ids.has(b.id)) return;
    if (b.g && b.g === g) siblings.push(b);
    else if (b.g) { if (!groups.has(b.g)) groups.set(b.g, []); groups.get(b.g).push(b); }
    else others.push(b);
  });
  groups.forEach(function (members) { others.push(frameRect(members)); });
  if (g && siblings.length) {
    // What the rest of the group already touches cannot be cured by moving these boxes:
    // they must stay off it themselves and must not pull the frame further over it.
    const rest = frameRect(siblings);
    direct = others.filter(function (o) { return hit(rest, o); }).map(function (o) { return { o: o, base: overlap(rest, o) }; });
    others = others.filter(function (o) { return !hit(rest, o); });
  }
  return { siblings: siblings, others: others, direct: direct, grouped: !!g };
}

function clear(ob, moved) {
  let outer = moved[0];
  if (ob.grouped) {
    for (const m of moved) {
      for (const s of ob.siblings) if (hit(m, s)) return false;
      for (const d of ob.direct) if (hit(m, d.o)) return false;
    }
    outer = frameRect(moved.concat(ob.siblings));
    for (const d of ob.direct) if (overlap(outer, d.o) > d.base) return false;
  }
  for (const o of ob.others) if (hit(outer, o)) return false;
  return true;
}

export function isFree(boxes, moving) { return clear(obstacles(boxes, moving), moving); }

// Smallest shift {dx, dy} in cells that puts the moving boxes on a free spot, by
// distance on screen. `boxes` is a Map of every placed box; entries with the moving
// ids are ignored. Optional bounds and pixel distance limit constrain the search.
//
// The search stops at the distance that carries the moving boxes past everything else.
// A whole box or a whole group is always free there. A single member of a group may
// have no free spot at all (its frame would stretch over other boxes whichever way it
// goes): then the result is {dx: 0, dy: 0, stuck: true}.
export function nearestFree(boxes, moving, within = null, limit = Infinity) {
  const ob = obstacles(boxes, moving);
  const every = bounds(Array.from(boxes.values()).concat(moving)), own = bounds(moving);
  const reach = Math.max(every.x1 - every.x0 + own.x1 - own.x0 + 4, Math.ceil((every.y1 - every.y0 + own.y1 - own.y0 + 8) / 2));
  function test(dx, dy) {
    if (within && (own.x0 + dx < within.x0 || own.x1 + dx > within.x1 ||
                   own.y0 + dy < within.y0 || own.y1 + dy > within.y1)) return false;
    return clear(ob, moving.map(function (m) { return { x: m.x + dx, y: m.y + dy, w: m.w, h: m.h }; }));
  }
  if (test(0, 0)) return { dx: 0, dy: 0 };
  let best = null, bestD = Infinity;
  for (let r = 1; r <= reach; r++) {
    const ry = 2 * r;   // a cell is about twice as wide as it is high
    if (Math.min(r * CW, (ry - 1) * CH) > Math.min(bestD, limit)) break;   // nothing nearer further out
    for (let dy = -ry; dy <= ry; dy++) {
      const step = Math.abs(dy) > ry - 2 ? 1 : 2 * r;   // full rows at the ring's top and bottom, else its two sides
      for (let dx = -r; dx <= r; dx += step) {
        const d = Math.hypot(dx * CW, dy * CH);
        if (d <= limit && d < bestD && test(dx, dy)) { best = { dx: dx, dy: dy }; bestD = d; }
      }
    }
  }
  return best || { dx: 0, dy: 0, stuck: true };
}

// Places entities one after another, each on the free spot nearest to where it wants
// to be. An entity is an array of boxes (one box, or the members of one group, already
// arranged relative to each other). Returns Map id -> box.
export function settle(entities) {
  const placed = new Map();
  for (const moving of entities) {
    const off = nearestFree(placed, moving);
    for (const b of moving) placed.set(b.id, Object.assign({}, b, { x: b.x + off.dx, y: b.y + off.dy }));
  }
  return placed;
}

function entitiesOf(boxes) {
  const groups = new Map(), list = [];
  boxes.forEach(function (b) {
    if (!b.g) { list.push([b]); return; }
    if (!groups.has(b.g)) { groups.set(b.g, []); list.push(groups.get(b.g)); }
    groups.get(b.g).push(b);
  });
  return list;
}

// Ids of boxes and groups that are closer than the gap to something else.
export function conflicts(boxes) {
  const internal = new Set(), external = new Set();
  const out = { boxes: new Set(), groups: new Set(), internal, external };
  const list = entitiesOf(boxes);
  const outer = list.map(function (e) { return e[0].g ? frameRect(e) : e[0]; });
  function mark(e) { external.add(e[0].g || e[0].id); if (e[0].g) out.groups.add(e[0].g); else out.boxes.add(e[0].id); }
  for (let i = 0; i < list.length; i++) {
    const e = list[i];
    if (e[0].g) {
      for (let a = 0; a < e.length; a++) for (let b = a + 1; b < e.length; b++) {
        if (hit(e[a], e[b])) { internal.add(e[a].id); internal.add(e[b].id); out.boxes.add(e[a].id); out.boxes.add(e[b].id); }
      }
    }
    for (let j = i + 1; j < list.length; j++) if (hit(outer[i], outer[j])) { mark(e); mark(list[j]); }
  }
  return out;
}

// Move only overlapping entities, treating all other positions as fixed. For the
// inside-group pass the siblings are supplied as standalone boxes.
export function tidy(boxes, keepFrame = false) {
  const list = entitiesOf(boxes).map(e => ({
    boxes: e,
    area: e.reduce((sum, b) => sum + b.w * b.h, 0),
  }));
  const work = new Map(boxes), moved = new Map();
  const distance = ({dx, dy}) => Math.hypot(dx * CW, dy * CH);
  const better = (a, b) => a && (!b || a.d < b.d || (a.d === b.d && a.entity.area < b.entity.area));
  // Each move lands clear of all other entities; it cannot create a new conflict
  // in this pass. No entity needs to move twice.
  for (let remaining = list.length; remaining > 0; remaining--) {
    const outer = list.map(({boxes: e}) => e[0].g ? frameRect(e) : e[0]);
    const frame = keepFrame ? bounds([...work.values()]) : null;
    const candidates = new Map(), contained = new Map();
    function candidate(entity, limit = Infinity) {
      const cache = limit === Infinity ? candidates : contained;
      // A miss at a smaller distance may succeed for a different opponent.
      if (!cache.has(entity) || cache.get(entity).limit < limit) {
        const off = nearestFree(work, entity.boxes, limit === Infinity ? null : frame, limit);
        cache.set(entity, {limit, move: off.stuck || (!off.dx && !off.dy) ? null : {entity, off, d: distance(off)}});
      }
      const {move} = cache.get(entity);
      return move && move.d <= limit ? move : null;
    }
    let best = null;
    for (let i = 0; i < list.length; i++) {
      for (let j = i + 1; j < list.length; j++) {
        if (!hit(outer[i], outer[j])) continue;
        const a = candidate(list[i]), b = candidate(list[j]);
        let move = better(a, b) ? a : b;
        if (frame && move) {
          const limit = 2 * move.d;
          const insideA = candidate(list[i], limit), insideB = candidate(list[j], limit);
          move = (better(insideA, insideB) ? insideA : insideB) || move;
        }
        if (better(move, best)) best = move;
      }
    }
    if (!best) break;
    const {entity, off} = best;
    entity.boxes = entity.boxes.map(b => {
      const p = {x: b.x + off.dx, y: b.y + off.dy};
      moved.set(b.id, p);
      const shifted = {...b, ...p};
      work.set(b.id, shifted);
      return shifted;
    });
  }
  return moved;
}

// Packs boxes into rows, in the order given, in a block about 1.6 times as wide as
// high. Returns Map id -> {x, y} relative to the block's top-left corner.
export function gather(members) {
  let total = 0;
  for (const m of members) total += m.w * CW * m.h * CH;
  const limit = Math.max(Math.sqrt(total * 1.6) / CW, Math.max.apply(null, members.map(function (m) { return m.w; })));
  const out = new Map();
  let x = 0, y = 0, rowH = 0;
  for (const m of members) {
    if (x > 0 && x + m.w > limit) { x = 0; y += rowH; rowH = 0; }
    out.set(m.id, { x: x, y: y });
    x += m.w; rowH = Math.max(rowH, m.h);
  }
  return out;
}
