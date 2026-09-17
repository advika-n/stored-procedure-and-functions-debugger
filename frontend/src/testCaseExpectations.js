// Expected-output baseline for the Test-Case Runner (frontend/src/TestCaseRunner.jsx).
//
// -- Why this file exists, and how these numbers were arrived at --------
// No expected-output contract existed anywhere in this repo before this
// phase (checked directly: no `expected*` field on any entry in
// `samples.js`, nothing under `backend/app`, nothing in git history) --
// so per this phase's own instruction ("flag it... rather than inventing
// one"), this is flagged rather than silently fabricated. What follows
// is NOT invented: every sample below is fully self-contained (every
// DECLARE uses a literal DEFAULT, no external IN params -- see
// samples.js's own header comment) and deterministic, so its correct
// final state is derivable by hand from the literal arithmetic in its
// source plus the one fixed fact this app's cursor samples depend on:
// the `products` table is always `[('Widget', 10), ('Gadget', 25),
// ('Gizmo', 15)]` in the persistent database (backend/app/user_db.py)
// this Test-Case Runner's own backend is talking to, unmodified by any
// sample here -- true for every sample in this file today (none of them
// write to `products` specifically), but no longer a fact this app can
// guarantee unconditionally the way the old per-request `:memory:`
// demo_db.py once did; a future sample that mutates `products` would
// need this assumption re-checked.
//
// Each value here was independently hand-computed from the sample's own
// source (see the comment above each entry), THEN cross-checked against
// a real run of the actual, unmodified tokenizer -> parser -> interpreter
// pipeline (in-process, backend/app, no mocks) -- every one matched
// exactly, which is what makes this a trustworthy regression baseline
// rather than a tautology (a mismatch would have meant either the hand
// math or the interpreter was wrong, and would have been investigated,
// not silently papered over).
//
// Contract per sample:
//   - PROCEDURE samples: `kind: 'variables'`, `variables: { name: value }`
//     checked against the FINAL step's variable snapshot (same shape as
//     `DebugStep.variables`, see interpreter.py/CLAUDE.md SS4) -- this
//     covers plain locals and OUT/INOUT params alike, since both show up
//     in that same snapshot.
//   - FUNCTION samples: `kind: 'return'`, `returnValue` checked against
//     the final step's `returnValue.value`.
//   - Either kind may ALSO carry an optional `tables: { tableName: [row,
//     ...] }` -- final row state for a table a SQL passthrough statement
//     touched (see backend/app/interpreter.py's "SQL passthrough
//     statements" section), checked against the LAST step in the whole
//     trace whose own `sql.tableName` matches that table (i.e. the
//     state right after that table's own final CREATE/INSERT/UPDATE/
//     DELETE -- see TestCaseRunner.jsx's `findFinalTableState`), NOT
//     just the very last step overall (which may belong to a different,
//     unrelated table, or to no table mutation at all). `variables`/
//     `returnValue` alone were never enough to express "the final
//     CONTENTS of a table" -- checking table state needed this
//     separate, additive field rather than force-fitting rows into
//     `variables`.
//
// Numeric comparisons in TestCaseRunner.jsx use a small epsilon (not
// strict ===) since this language's arithmetic is floating point (e.g.
// AntiPatternShowcase's `average` is the repeating decimal 50/3).
//
// If a new sample is ever added to samples.js with no entry here, the
// Test-Case Runner surfaces it as "no expected output defined" rather
// than silently skipping it or inventing a value for it.

export const TEST_CASE_EXPECTATIONS = {
  // total = 25*4 = 100; tax = 100*0.08 = 8; total = 100+8 = 108
  CalculateTotal: {
    kind: 'variables',
    variables: { price: 25, quantity: 4, tax: 8, total: 108 },
  },

  // total = 20*6 = 120; 120 > 100 -> discount = 120*0.1 = 12; total = 120-12 = 108
  CalculateDiscount: {
    kind: 'variables',
    variables: { price: 20, quantity: 6, total: 108, discount: 12 },
  },

  // score=82 -> score>59 true -> score>89 false -> grade=3
  GradeClassifier: {
    kind: 'variables',
    variables: { score: 82, grade: 3 },
  },

  // total starts 0, counter 1; loop while total<15: (0,1)->1,2 ->3,3 ->6,4
  // ->10,5 ->15,6; 15<15 false, stop.
  SumUntilLimit: {
    kind: 'variables',
    variables: { total: 15, counter: 6 },
  },

  // units=6>5 -> unitPrice=8; loop 6 times adding 8 each -> total=48, counter=6
  TieredPricingCalculator: {
    kind: 'variables',
    variables: { units: 6, unitPrice: 8, total: 48, counter: 6 },
  },

  // Cursor over products (Widget 10, Gadget 25, Gizmo 15): total=10+25+15=50,
  // last FETCH leaves item_name/item_price as the final row, Gizmo/15.
  ProductPriceTotal: {
    kind: 'variables',
    variables: { total: 50, item_name: 'Gizmo', item_price: 15 },
  },

  // WHERE price > 1000 matches none of the 3 demo rows: the first FETCH
  // fires NOT_FOUND (handled: done=1), the loop body's SET statements
  // never run, so total/count stay 0; SET average = total/count then
  // fires DIVISION_BY_ZERO (handled: average=0).
  SafeAverageWithHandlers: {
    kind: 'variables',
    variables: { total: 0, count: 0, average: 0, done: 1, item_name: '', item_price: 0 },
  },

  // taxAmount (OUT) = 150*0.08 = 12
  ComputeTax: {
    kind: 'variables',
    variables: { taxAmount: 12, price: 150, rate: 0.08 },
  },

  // total = 200*10 = 2000; 2000>1000 -> RETURN 2000*0.9 = 1800
  GetDiscountedPrice: {
    kind: 'return',
    returnValue: 1800,
  },

  // value doubles from 5 each iteration: 10,20,40,80 (i=1,2,3,4) -- 80>50
  // on i=4's pass, RETURN i (4) before the trailing RETURN -1 is reached.
  FindFirstOverLimit: {
    kind: 'return',
    returnValue: 4,
  },

  // ComputeSubtotal(20, 6, OUT subtotal) -> subtotal = 20*6 = 120;
  // grandTotal = 120 + 120*0.08 = 129.6 (values land back in the
  // OrderTotal top-level frame, the one the final step belongs to).
  OrderTotal: {
    kind: 'variables',
    variables: { price: 20, quantity: 6, taxRate: 0.08, subtotal: 120, grandTotal: 129.6 },
  },

  // Fact(5)->Fact(4)->Fact(3)->Fact(2)->Fact(1)=1; unwinding:
  // Fact(2)=2*1=2, Fact(3)=3*2=6, Fact(4)=4*6=24, Fact(5)=5*24=120;
  // ComputeFactorial's own `result` (top-level frame) ends at 120.
  RecursiveFactorial: {
    kind: 'variables',
    variables: { result: 120 },
  },

  // Same cursor sum as ProductPriceTotal: total=50, count=3, last row
  // Gizmo/15. The nested loop is a genuine, deliberate anti-pattern bug
  // in the sample itself: `inner` is declared ONCE before the outer
  // loop, not reset each outer pass, so the inner loop only actually
  // executes on the outer loop's first pass (bonus 0->300, inner 0->3);
  // the next two outer passes see inner already at 3 and skip the inner
  // loop entirely. bonus=300 after the nested loops, then the trailing
  // `SET bonus = bonus + 100;` makes it 400. average = 50/3 (repeating).
  AntiPatternShowcase: {
    kind: 'variables',
    variables: {
      total: 50,
      count: 3,
      average: 50 / 3,
      item_name: 'Gizmo',
      item_price: 15,
      outer: 3,
      inner: 3,
      bonus: 400,
    },
  },

  // Added for the "function calls inside procedures" phase, testing the
  // new FunctionCallExpr the same way OrderTotal/RecursiveFactorial test
  // CALL -- this sample is a ProgramNode too (a FUNCTION + a PROCEDURE
  // chained together), so the checked variables are the entry procedure
  // CheckoutTotal's OWN top-level frame, same convention as those two.
  //
  // subtotal = price*quantity = 250*3 = 750.
  // ComputeDiscountedPrice(price, rate) = price - (price*rate), called
  // TWICE:
  //   1. In the IF's own condition: ComputeDiscountedPrice(750, 0.1)
  //      = 750 - 750*0.1 = 750 - 75 = 675; 675 < 700 -> THEN branch taken.
  //   2. In the THEN branch's assignment: ComputeDiscountedPrice(750, 0.2)
  //      = 750 - 750*0.2 = 750 - 150 = 600 -> finalTotal.
  // The ELSE branch's own ComputeDiscountedPrice(750, 0.1) call never
  // executes at runtime (the condition was true), so it doesn't factor
  // into the expected final state at all.
  CheckoutTotal: {
    kind: 'variables',
    variables: { price: 250, quantity: 3, subtotal: 750, finalTotal: 600 },
  },

  // Added for the CASE statement support phase -- exercises both CASE
  // forms in one sample (see samples.js's own comment for why the two
  // genuine Advisor findings on this sample -- magic-number, unused-
  // variable -- are left in rather than dodged).
  //
  // Simple CASE: tier = 2 (DEFAULT) matches WHEN 2 exactly ->
  // discountRate = 0.1 (WHEN 1/WHEN 3/ELSE never run).
  // total = (quantity * unitPrice) * (1 - discountRate)
  //       = (12 * 15) * (1 - 0.1) = 180 * 0.9 = 162.
  // Searched CASE: is total > 200? 162 > 200 is false. Is total > 100?
  // 162 > 100 is true -> sizeLabel = 20 (the ELSE, 10, never runs).
  ClassifyOrder: {
    kind: 'variables',
    variables: {
      quantity: 12,
      unitPrice: 15,
      tier: 2,
      discountRate: 0.1,
      total: 162,
      sizeLabel: 20,
    },
  },

  // Added for the LOOP/LEAVE support phase -- see samples.js's own
  // comment for the full trace narrative. i=1's inner pass checks j=1..5
  // (1+1=2, 1+2=3, 1+3=4, 1+4=5, 1+5=6 -- none equal target=7), so the
  // inner LOOP's own unlabeled `LEAVE;` fires once j reaches 6 (j>5),
  // and the outer loop advances i to 2. i=2's inner pass: 2+1=3, 2+2=4,
  // 2+3=5, 2+4=6, 2+5=7 -- MATCH at j=5, so foundI=2/foundJ=5 are set
  // and `LEAVE outer;` fires immediately (the outer loop's own trailing
  // `SET i = i + 1;` never runs). Cross-checked against a real
  // interpreter run.
  FindPairSum: {
    kind: 'variables',
    variables: { target: 7, i: 2, j: 5, foundI: 2, foundJ: 5 },
  },

  // Added for the SQL passthrough statements phase (CREATE TABLE /
  // INSERT / UPDATE / DELETE, raw SQL against the real persistent
  // database) -- see samples.js's own comment for the full narrative.
  // Three rows INSERTed: (1,'Widget',8,10), (2,'Gadget',0,25),
  // (3,'Gizmo',15,15). First UPDATE (qty = qty+5 WHERE qty<10) matches
  // Widget (8<10) and Gadget (0<10), NOT Gizmo (15<10 is false): Widget's
  // qty -> 13, Gadget's qty -> 5. Second UPDATE (price = price-2 WHERE
  // price>12) matches Gadget (25>12) and Gizmo (15>12), NOT Widget
  // (10>12 is false): Gadget's price -> 23, Gizmo's price -> 13. DELETE
  // WHERE id=2 then removes Gadget outright (by id, regardless of its
  // now-restocked qty/discounted price), leaving exactly Widget
  // (13, 10) and Gizmo (15, 13) -- cross-checked against a real
  // interpreter run (this module has no variable checks: ManageInventory
  // declares none -- every value lives in the table itself).
  ManageInventory: {
    kind: 'variables',
    variables: {},
    tables: {
      inventory: [
        { id: 1, item: 'Widget', qty: 13, price: 10 },
        { id: 3, item: 'Gizmo', qty: 15, price: 13 },
      ],
    },
  },

  // Added for the merged Debugger/SQL Console phase -- see samples.js's
  // own comment for the full narrative. Three rows INSERTed:
  // (1,'Widget',4,10), (2,'Gadget',2,25), (3,'Gizmo',6,15). The UPDATE
  // (qty = qty+10 WHERE qty<5) matches Widget (4<5) and Gadget (2<5),
  // NOT Gizmo (6<5 is false): Widget's qty -> 14, Gadget's qty -> 12.
  // The cursor then sums qty*price over all three rows in insertion
  // order: 14*10 + 12*25 + 6*15 = 140 + 300 + 90 = 530 -- cross-checked
  // against a real interpreter run.
  InventoryValueReport: {
    kind: 'variables',
    variables: { totalValue: 530 },
    tables: {
      stock: [
        { id: 1, name: 'Widget', qty: 14, price: 10 },
        { id: 2, name: 'Gadget', qty: 12, price: 25 },
        { id: 3, name: 'Gizmo', qty: 6, price: 15 },
      ],
    },
  },

  // Added for the comparison-operators + SELECT...INTO phase -- see
  // samples.js's own comment. score=82: <> 100 is true (isPerfect=0);
  // >= 90 is false; >= 75 is true, so grade lands on 'B' without ever
  // reaching the <= 40 rung -- cross-checked against a real interpreter
  // run.
  OperatorShowcase: {
    kind: 'variables',
    variables: { grade: 'B', isPerfect: 0 },
  },

  // foundScore comes from the Ada lookup (95) and is untouched by the
  // second (Nonexistent) lookup, which matches no row -- a
  // SelectIntoStatement's NOT_FOUND path assigns no target variable at
  // all, same as an exhausted cursor FETCH already doesn't (see
  // app.interpreter's "SELECT ... INTO" module docstring section).
  // missingHandled reads back notFoundFlag, which the registered
  // CONTINUE HANDLER set to 1 when that second lookup triggered
  // NOT_FOUND -- cross-checked against a real interpreter run. `players`
  // table state reflects both INSERTs (the last write-with-snapshot
  // step on that table); the two SELECT...INTO lookups after it are
  // reads, not writes, so they don't change this.
  LookupOnePlayer: {
    kind: 'variables',
    variables: { foundScore: 95, missingHandled: 1 },
    tables: {
      players: [
        { id: 1, name: 'Ada', score: 95 },
        { id: 2, name: 'Grace', score: 88 },
      ],
    },
  },
}
