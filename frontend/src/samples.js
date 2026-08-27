// A small library of sample procedures for the picker. Each uses only
// the supported grammar (DECLARE / SET / IF-ELSE / WHILE -- no >=, <=,
// or procedure parameters, since the tokenizer/parser don't support
// those) and is fully self-contained via DECLARE ... DEFAULT, so any
// sample can be loaded and run with no extra setup.
//
// The last two samples use cursors and exception handlers (see
// backend/app/parser.py and backend/app/interpreter.py for the exact
// supported grammar and scope). Their cursor queries run against a
// small, fixed, auto-seeded demo table -- products(name, price), 3
// rows -- that every /debug request gets for free (see
// backend/app/demo_db.py); there's no schema-editing feature, so
// cursor-based procedures you write yourself must query that same
// `products` table (or `WHERE` filters over it) to have any rows to
// work with.

export const SAMPLES = [
  {
    name: 'CalculateTotal',
    description: 'Straight-line arithmetic assignments with no branching -- the simplest possible trace, good as a first look.',
    code: `DECLARE price NUMBER DEFAULT 25;
DECLARE quantity NUMBER DEFAULT 4;
DECLARE tax NUMBER DEFAULT 0;
DECLARE total NUMBER DEFAULT 0;
SET total = price * quantity;
SET tax = total * 0.08;
SET total = total + tax;
`,
  },
  {
    name: 'CalculateDiscount',
    description: 'Applies a single IF/ELSE threshold to pick a discount rate -- the running example used throughout this tool.',
    code: `DECLARE price NUMBER DEFAULT 20;
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
`,
  },
  {
    name: 'GradeClassifier',
    description: "Nests an IF/ELSE inside another IF's THEN branch to classify a score into a letter grade.",
    code: `DECLARE score NUMBER DEFAULT 82;
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
`,
  },
  {
    name: 'SumUntilLimit',
    description: 'A WHILE loop accumulates a running total until it reaches a limit -- good for watching the loop counter update.',
    code: `DECLARE total NUMBER DEFAULT 0;
DECLARE counter NUMBER DEFAULT 1;
WHILE total < 15 DO
    SET total = total + counter;
    SET counter = counter + 1;
END WHILE;
`,
  },
  {
    name: 'TieredPricingCalculator',
    description: 'Picks a pricing tier with IF/ELSE, then applies it per unit in a WHILE loop -- combines both constructs in one trace.',
    code: `DECLARE units NUMBER DEFAULT 6;
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
`,
  },
  {
    name: 'ProductPriceTotal',
    description: 'Opens a cursor over the built-in `products` demo table (3 rows) and sums every price with a WHILE cur%FOUND loop -- a first, minimal cursor walkthrough.',
    code: `DECLARE total NUMBER DEFAULT 0;
DECLARE item_name STRING DEFAULT '';
DECLARE item_price NUMBER DEFAULT 0;
DECLARE prod_cursor CURSOR FOR SELECT name, price FROM products;
OPEN prod_cursor;
WHILE prod_cursor%FOUND DO
    FETCH prod_cursor INTO item_name, item_price;
    SET total = total + item_price;
END WHILE;
CLOSE prod_cursor;
`,
  },
  {
    name: 'SafeAverageWithHandlers',
    description: 'Declares CONTINUE HANDLERs for NOT_FOUND and DIVISION_BY_ZERO, then opens a cursor whose WHERE clause matches none of the demo rows -- both conditions genuinely fire, and the procedure recovers gracefully instead of crashing.',
    code: `DECLARE total NUMBER DEFAULT 0;
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
`,
  },
]
