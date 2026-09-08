-- RedefineTables
PRAGMA defer_foreign_keys=ON;
PRAGMA foreign_keys=OFF;
CREATE TABLE "new_Queue" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "createdAt" DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "songName" TEXT NOT NULL,
    "artist" TEXT NOT NULL,
    "requester" TEXT NOT NULL,
    "url" TEXT NOT NULL,
    "position" REAL NOT NULL,
    CONSTRAINT "Queue_requester_fkey" FOREIGN KEY ("requester") REFERENCES "User" ("username") ON DELETE RESTRICT ON UPDATE CASCADE
);
INSERT INTO "new_Queue" ("artist", "createdAt", "id", "position", "requester", "url", "songName") SELECT "artist", "createdAt", "id", "position", "requester", "url", "name" FROM "Queue";
DROP TABLE "Queue";
ALTER TABLE "new_Queue" RENAME TO "Queue";
CREATE INDEX "Queue_position_idx" ON "Queue"("position");
PRAGMA foreign_keys=ON;
PRAGMA defer_foreign_keys=OFF;
