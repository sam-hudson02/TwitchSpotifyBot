/*
  Warnings:

  - Added the required column `position` to the `Queue` table without a default value. This is not possible if the table is not empty.

*/
-- RedefineTables
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Queue" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL,
    "artist" TEXT NOT NULL,
    "requester" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "position" INTEGER NOT NULL
);
INSERT INTO "new_Queue" ("artist", "id", "name", "requester", "url") SELECT "artist", "id", "name", "requester", "url" FROM "Queue";
DROP TABLE "Queue";
ALTER TABLE "new_Queue" RENAME TO "Queue";
PRAGMA foreign_key_check;
PRAGMA foreign_keys=ON;
