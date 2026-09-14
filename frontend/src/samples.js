// A small library of sample procedures and functions for the picker.
// Each uses only the supported grammar (DECLARE / SET / IF-ELSE / WHILE
// -- no >=, <=, since the tokenizer/parser don't support those) and is
// fully self-contained via DECLARE ... DEFAULT, so any sample can be
// loaded and run with no extra setup.
//
// Every entry carries a `kind`, either 'PROCEDURE' or 'FUNCTION' --
// purely a picker label (see the sample-kind-tag next to each name in
// DebuggerPage.jsx), not something the interpreter needs; it's derived
// once here rather than re-parsed from `code` at render time.
//
// Decision (asked for explicitly when CREATE PROCEDURE support was
// added): every procedure sample here uses the full CREATE PROCEDURE(...)
// BEGIN...END wrapper, not the bare statement-list form. Migrating was
// a pure find-and-replace, not a parser change -- every sample here
// already used empty parens' worth of external input (all self-contain
// their values via DECLARE ... DEFAULT; the frontend always sends
// params: {} today, so none of them could have relied on externally
// supplied params anyway) -- and it makes the sample library visually
// consistent with the syntax the Theory tab actually teaches, instead
// of contradicting it. The bare, wrapper-less form is NOT gone: it's
// the permanent backward-compatibility path (see backend/app/parser.py's
// module docstring), still fully supported, still what every History
// entry saved before this change is stored as -- it's just no longer
// what any *sample* demonstrates, since there's no behavioral reason
// left to prefer it for a fresh one.
//
// ComputeTax was the first sample to use a declared parameter (an OUT
// param specifically -- an IN param would need the frontend to
// actually collect and send a value, which it doesn't do yet, so a
// sample requiring one would break the moment it's run; OUT needs no
// external input at all, so it's safe to demo live right now). The two
// FUNCTION samples below have the same constraint: function params
// never have a mode (no OUT to fall back on), so both are zero-param
// and self-contained via DECLARE ... DEFAULT, same as every PROCEDURE
// sample -- not because that's the interesting way to write a
// function, just because it's the only form guaranteed to run without
// a params-collection UI that doesn't exist yet.
//
// The cursor-based samples run their queries against a small, fixed,
// auto-seeded demo table -- products(name, price), 3 rows -- that
// every /debug request gets for free (see backend/app/demo_db.py);
// there's no schema-editing feature, so cursor-based procedures you
// write yourself must query that same `products` table (or `WHERE`
// filters over it) to have any rows to work with.

export const SAMPLES = [
  {
    name: 'CalculateTotal',
    kind: 'PROCEDURE',
    description: 'Straight-line arithmetic assignments with no branching -- the simplest possible trace, good as a first look.',
    code: `CREATE PROCEDURE CalculateTotal()
BEGIN
    DECLARE price NUMBER DEFAULT 25;
    DECLARE quantity NUMBER DEFAULT 4;
    DECLARE tax NUMBER DEFAULT 0;
    DECLARE total NUMBER DEFAULT 0;
    SET total = price * quantity;
    SET tax = total * 0.08;
    SET total = total + tax;
END
`,
  },
  {
    name: 'CalculateDiscount',
    kind: 'PROCEDURE',
    description: 'Applies a single IF/ELSE threshold to pick a discount rate -- the running example used throughout this tool.',
    code: `CREATE PROCEDURE CalculateDiscount()
BEGIN
    DECLARE price NUMBER DEFAULT 20;
    DECLARE quantity NUMBER DEFAULT 6;
    DECLARE total NUMBER DEFAULT 0;
    DECLARE discount NUMBER DEFAULT 0;
    SET total = price * quantity;
    IF total > 100 THEN
        SET discount = total * 0.1;
    ELSE
        SET discount = total * 0.05;
    END IF;
    SET total = total - discount;
END
`,
  },
  {
    name: 'GradeClassifier',
    kind: 'PROCEDURE',
    description: "Nests an IF/ELSE inside another IF's THEN branch to classify a score into a letter grade.",
    code: `CREATE PROCEDURE GradeClassifier()
BEGIN
    DECLARE score NUMBER DEFAULT 82;
    DECLARE grade NUMBER DEFAULT 0;
    IF score > 59 THEN
        IF score > 89 THEN
            SET grade = 4;
        ELSE
            SET grade = 3;
        END IF;
    ELSE
        SET grade = 2;
    END IF;
END
`,
  },
  {
    name: 'SumUntilLimit',
    kind: 'PROCEDURE',
    description: 'A WHILE loop accumulates a running total until it reaches a limit -- good for watching the loop counter update.',
    code: `CREATE PROCEDURE SumUntilLimit()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    DECLARE counter NUMBER DEFAULT 1;
    WHILE total < 15 DO
        SET total = total + counter;
        SET counter = counter + 1;
    END WHILE;
END
`,
  },
  {
    name: 'TieredPricingCalculator',
    kind: 'PROCEDURE',
    description: 'Picks a pricing tier with IF/ELSE, then applies it per unit in a WHILE loop -- combines both constructs in one trace.',
    code: `CREATE PROCEDURE TieredPricingCalculator()
BEGIN
    DECLARE units NUMBER DEFAULT 6;
    DECLARE unitPrice NUMBER DEFAULT 0;
    DECLARE total NUMBER DEFAULT 0;
    DECLARE counter NUMBER DEFAULT 0;
    IF units > 5 THEN
        SET unitPrice = 8;
    ELSE
        SET unitPrice = 10;
    END IF;
    WHILE counter < units DO
        SET total = total + unitPrice;
        SET counter = counter + 1;
    END WHILE;
END
`,
  },
  {
    name: 'ProductPriceTotal',
    kind: 'PROCEDURE',
    description: 'Opens a cursor over the built-in `products` demo table (3 rows) and sums every price with a WHILE cur%FOUND loop -- a first, minimal cursor walkthrough.',
    code: `CREATE PROCEDURE ProductPriceTotal()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    DECLARE item_name STRING DEFAULT '';
    DECLARE item_price NUMBER DEFAULT 0;
    DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products;
    OPEN prod_cursor;
    WHILE prod_cursor%FOUND DO
        FETCH prod_cursor INTO item_name, item_price;
        SET total = total + item_price;
    END WHILE;
    CLOSE prod_cursor;
END
`,
  },
  {
    name: 'SafeAverageWithHandlers',
    kind: 'PROCEDURE',
    description: 'Declares CONTINUE HANDLERs for NOT_FOUND and DIVISION_BY_ZERO, then opens a cursor whose WHERE clause matches none of the demo rows -- both conditions genuinely fire, and the procedure recovers gracefully instead of crashing.',
    code: `CREATE PROCEDURE SafeAverageWithHandlers()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    DECLARE count NUMBER DEFAULT 0;
    DECLARE average NUMBER DEFAULT -1;
    DECLARE done NUMBER DEFAULT 0;
    DECLARE item_name STRING DEFAULT '';
    DECLARE item_price NUMBER DEFAULT 0;
    DECLARE CONTINUE HANDLER FOR NOT_FOUND SET done = 1;
    DECLARE CONTINUE HANDLER FOR DIVISION_BY_ZERO SET average = 0;
    DECLARE premium_cursor CURSOR FOR SELECT name, price FROM products WHERE price > 1000;
    OPEN premium_cursor;
    WHILE done = 0 DO
        FETCH premium_cursor INTO item_name, item_price;
        IF done = 0 THEN
            SET total = total + item_price;
            SET count = count + 1;
        END IF;
    END WHILE;
    CLOSE premium_cursor;
    SET average = total / count;
END
`,
  },
  {
    name: 'ComputeTax',
    kind: 'PROCEDURE',
    description: 'A first look at a declared OUT parameter: the procedure computes a value internally and exposes it through `taxAmount`, visible (and flagged isOutput) in the variable table right alongside every local.',
    code: `CREATE PROCEDURE ComputeTax(OUT taxAmount NUMBER)
BEGIN
    DECLARE price NUMBER DEFAULT 150;
    DECLARE rate NUMBER DEFAULT 0.08;
    SET taxAmount = price * rate;
END
`,
  },
  {
    name: 'GetDiscountedPrice',
    kind: 'FUNCTION',
    description: 'The canonical CREATE FUNCTION example: RETURN inside an IF/ELSE picks the discounted or plain total -- step to either branch’s RETURN and watch the Return Value panel appear with that exact value.',
    code: `CREATE FUNCTION GetDiscountedPrice()
RETURNS DECIMAL
BEGIN
    DECLARE price DECIMAL DEFAULT 200;
    DECLARE quantity INT DEFAULT 10;
    DECLARE total DECIMAL;
    SET total = price * quantity;
    IF total > 1000 THEN
        RETURN total * 0.9;
    ELSE
        RETURN total;
    END IF;
END
`,
  },
  {
    name: 'FindFirstOverLimit',
    kind: 'FUNCTION',
    description: 'RETURN from inside a WHILE loop, not just an IF/ELSE -- doubles a value each iteration and returns the iteration count the instant it crosses a limit, so the trailing fallback RETURN never executes.',
    code: `CREATE FUNCTION FindFirstOverLimit()
RETURNS NUMBER
BEGIN
    DECLARE limit NUMBER DEFAULT 50;
    DECLARE value NUMBER DEFAULT 5;
    DECLARE i NUMBER DEFAULT 1;
    WHILE i < 20 DO
        SET value = value * 2;
        IF value > limit THEN
            RETURN i;
        END IF;
        SET i = i + 1;
    END WHILE;
    RETURN -1;
END
`,
  },
  // Added specifically for the Call Stack phase -- demonstrates
  // backend/app/interpreter.py's CALL support (a prior phase) with a
  // real, live sample now that the frontend actually renders it (see
  // the Call Stack panel in DebuggerPage.jsx). Two chained
  // CREATE PROCEDURE definitions parse to a single `ProgramNode` (see
  // backend/app/parser.py's module docstring); the LAST one, OrderTotal,
  // is the entry point that runs. Deliberately zero-param at the top
  // level (same "no external IN-param-collection UI yet" constraint
  // documented above) -- OrderTotal self-contains its own values via
  // DECLARE ... DEFAULT and only passes them onward via CALL.
  {
    name: 'OrderTotal',
    kind: 'PROCEDURE',
    description: 'OrderTotal CALLs a helper, ComputeSubtotal, passing an OUT parameter back -- step into the CALL and watch the Call Stack panel grow from 1 frame to 2, then shrink back to 1 once ComputeSubtotal returns.',
    code: `CREATE PROCEDURE ComputeSubtotal(IN price NUMBER, IN quantity NUMBER, OUT subtotal NUMBER)
BEGIN
    SET subtotal = price * quantity;
END;

CREATE PROCEDURE OrderTotal()
BEGIN
    DECLARE price NUMBER DEFAULT 20;
    DECLARE quantity NUMBER DEFAULT 6;
    DECLARE taxRate NUMBER DEFAULT 0.08;
    DECLARE subtotal NUMBER DEFAULT 0;
    DECLARE grandTotal NUMBER DEFAULT 0;
    CALL ComputeSubtotal(price, quantity, subtotal);
    SET grandTotal = subtotal + subtotal * taxRate;
END
`,
  },
  // Also added for the Call Stack phase: a self-recursive CALL (Fact
  // calls itself -- see app.interpreter's module docstring on how the
  // entry procedure is registered under its own name to make this work
  // with no extra syntax) so the Call Stack panel can be exercised past
  // depth 2. ComputeFactorial (the entry point, last definition) takes
  // no params and CALLs Fact with a literal argument, for the same
  // no-external-IN-param-collection-UI reason as OrderTotal above. The
  // trailing `SET result = result + 0;` is a deliberate no-op: without
  // some statement after the CALL, the trace's last step would be deep
  // inside Fact's own frame (whose OUT-propagated value never gets a
  // step of its own back in ComputeFactorial's frame), so the demo would
  // never show the Call Stack panel actually unwinding back to 1 frame
  // with a final answer visible at the top level.
  {
    name: 'RecursiveFactorial',
    kind: 'PROCEDURE',
    description: 'Fact CALLs itself to compute 5! -- step through it to watch the Call Stack panel grow several frames deep (one per pending multiplication) and then unwind back to 1.',
    code: `CREATE PROCEDURE Fact(IN n NUMBER, OUT result NUMBER)
BEGIN
    DECLARE sub NUMBER DEFAULT 1;
    IF n > 1 THEN
        CALL Fact(n - 1, sub);
        SET result = n * sub;
    ELSE
        SET result = 1;
    END IF;
END;

CREATE PROCEDURE ComputeFactorial()
BEGIN
    DECLARE result NUMBER DEFAULT 0;
    CALL Fact(5, result);
    SET result = result + 0;
END
`,
  },
  // Added specifically for the SQL Anti-Pattern Advisor phase -- unlike
  // every sample above, this one is deliberately *bad*, so the six
  // detectable anti-patterns (see backend/app/advisor.py) have a live,
  // runnable demo to show up on the moment someone loads it and clicks
  // Debug. It still executes successfully end to end (3 demo rows, a
  // small fixed-count nested loop) -- the point is that its *structure*
  // has real issues worth flagging, not that it crashes.
  {
    name: 'AntiPatternShowcase',
    kind: 'PROCEDURE',
    description: 'New for this phase -- deliberately bad on purpose: SELECT *, a cursor loop that only sums rows, nested loops, a hard-coded value repeated twice, an unhandled division, and a cursor left open. Load it and click Debug to see every anti-pattern the Advisor catches, flagged live below the editor.',
    code: `CREATE PROCEDURE AntiPatternShowcase()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    DECLARE count NUMBER DEFAULT 0;
    DECLARE average NUMBER DEFAULT 0;
    DECLARE item_name STRING DEFAULT '';
    DECLARE item_price NUMBER DEFAULT 0;
    DECLARE outer NUMBER DEFAULT 0;
    DECLARE inner NUMBER DEFAULT 0;
    DECLARE bonus NUMBER DEFAULT 0;
    DECLARE all_cursor CURSOR FOR SELECT * FROM products;
    OPEN all_cursor;
    WHILE all_cursor%FOUND DO
        FETCH all_cursor INTO item_name, item_price;
        SET total = total + item_price;
        SET count = count + 1;
    END WHILE;
    WHILE outer < 3 DO
        WHILE inner < 3 DO
            SET bonus = bonus + 100;
            SET inner = inner + 1;
        END WHILE;
        SET outer = outer + 1;
    END WHILE;
    SET bonus = bonus + 100;
    SET average = total / count;
END
`,
  },
  // Added specifically for the Extended Static Analysis Warnings phase --
  // same reasoning as AntiPatternShowcase above: a small, deliberately
  // flawed, live demo of the three new checks (backend/app/advisor.py SS7-9)
  // so they show up the moment someone loads this and clicks Debug,
  // rather than only being provable via backend unit tests. Still
  // executes successfully end to end (the interpreter genuinely reaches
  // the early RETURN and stops there -- see the comments below) -- the
  // point is the *structure* has real issues, not that it crashes.
  {
    name: 'StaticAnalysisShowcase',
    kind: 'PROCEDURE',
    description: 'New for this phase -- deliberately bad on purpose: a value overwritten before it’s ever read, a variable that’s set but never read, dead code after an early RETURN, and an IF branch that can never run. Load it and click Debug to see all four new warnings flagged live below the editor.',
    code: `CREATE PROCEDURE StaticAnalysisShowcase()
BEGIN
    DECLARE total NUMBER DEFAULT 0;
    DECLARE label NUMBER DEFAULT 0;
    SET total = 5;
    SET total = 200;
    SET label = 1;
    IF total > 100 THEN
        RETURN 0;
        SET total = -1;
    END IF;
    IF 1 > 2 THEN
        SET label = 99;
    END IF;
END
`,
  },
  // Added specifically for the "function calls inside procedures" phase --
  // a procedure invoking a FUNCTION from within an expression (backend/
  // app/parser.py's FunctionCallExpr, backend/app/interpreter.py's
  // `_evaluate_function_call`), distinct from CALL (which can only target
  // a procedure and never produces a value -- see OrderTotal/
  // RecursiveFactorial above for that). ComputeDiscountedPrice is called
  // TWICE: once inside the IF's own condition (its return value compared
  // against a literal), and once more inside the taken branch's
  // assignment -- exercising both positions the phase asked for in one
  // small sample, and proving the function is genuinely re-entrant (two
  // separate invocations, not a cached/one-shot call).
  {
    name: 'CheckoutTotal',
    kind: 'PROCEDURE',
    description: 'CheckoutTotal calls a FUNCTION, ComputeDiscountedPrice, from inside an expression -- once in an IF condition, once more in the assignment that follows -- step through it and watch the Call Stack panel show the function as its own frame, twice.',
    code: `CREATE FUNCTION ComputeDiscountedPrice(price NUMBER, rate NUMBER) RETURNS NUMBER
BEGIN
    RETURN price - (price * rate);
END;

CREATE PROCEDURE CheckoutTotal()
BEGIN
    DECLARE price NUMBER DEFAULT 250;
    DECLARE quantity NUMBER DEFAULT 3;
    DECLARE subtotal NUMBER DEFAULT 0;
    DECLARE finalTotal NUMBER DEFAULT 0;
    SET subtotal = price * quantity;
    IF ComputeDiscountedPrice(subtotal, 0.1) < 700 THEN
        SET finalTotal = ComputeDiscountedPrice(subtotal, 0.2);
    ELSE
        SET finalTotal = ComputeDiscountedPrice(subtotal, 0.1);
    END IF;
END
`,
  },
  // Added specifically for the CASE statement support phase -- exercises
  // BOTH CASE forms (backend/app/parser.py's "CASE statement" section) in
  // one sample, the way this phase's prompt asked for: a SIMPLE CASE
  // (`CASE tier WHEN 1 THEN ...`) picks a discount rate off a tier code,
  // then a SEARCHED CASE (`CASE WHEN total > 200 THEN ...`) classifies
  // the resulting total into a size label. Two genuine, minor
  // Anti-Pattern Advisor findings are expected and left in on purpose,
  // not dodged: `magic-number` (tier's own `DEFAULT 2` collides with its
  // own `WHEN 2` -- an entirely natural coincidence for a tier-code demo,
  // not a fabricated one) and `unused-variable` on `sizeLabel` (the
  // classification result is left as the procedure's final state, same
  // already-accepted "final result variable" pattern GradeClassifier's
  // own `grade` already demonstrates elsewhere in this library).
  {
    name: 'ClassifyOrder',
    kind: 'PROCEDURE',
    description: 'Exercises both CASE forms: a SIMPLE CASE (CASE tier WHEN 1 THEN ...) picks a discount rate off a tier code, then a SEARCHED CASE (CASE WHEN total > 200 THEN ...) classifies the discounted total into a size label -- step through to watch the flowchart light up whichever WHEN clause matched.',
    code: `CREATE PROCEDURE ClassifyOrder()
BEGIN
    DECLARE quantity NUMBER DEFAULT 12;
    DECLARE unitPrice NUMBER DEFAULT 15;
    DECLARE tier NUMBER DEFAULT 2;
    DECLARE discountRate NUMBER DEFAULT 0;
    DECLARE total NUMBER DEFAULT 0;
    DECLARE sizeLabel NUMBER DEFAULT 0;
    CASE tier
        WHEN 1 THEN
            SET discountRate = 0.05;
        WHEN 2 THEN
            SET discountRate = 0.1;
        WHEN 3 THEN
            SET discountRate = 0.15;
        ELSE
            SET discountRate = 0;
    END CASE;
    SET total = (quantity * unitPrice) * (1 - discountRate);
    CASE
        WHEN total > 200 THEN
            SET sizeLabel = 30;
        WHEN total > 100 THEN
            SET sizeLabel = 20;
        ELSE
            SET sizeLabel = 10;
    END CASE;
END
`,
  },
]
