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
]
