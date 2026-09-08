-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_User" (
    "username" TEXT NOT NULL,
    "ban" BOOLEAN NOT NULL DEFAULT false,
    "dj" BOOLEAN NOT NULL DEFAULT false,
    "admin" BOOLEAN NOT NULL DEFAULT false,
    "requests" INTEGER NOT NULL DEFAULT 0,
    "rates" INTEGER NOT NULL DEFAULT 0,
    "ratesGiven" INTEGER NOT NULL DEFAULT 0
);
INSERT INTO "new_User" ("username", "ban", "dj", "admin", "requests", "rates", "ratesGiven") SELECT "username", "ban", "mod", "admin", "requests", "rates", "ratesGiven" FROM "User";
DROP TABLE "User";
ALTER TABLE "new_User" RENAME TO "User";
CREATE UNIQUE INDEX "User_username_key" ON "User"("username");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
