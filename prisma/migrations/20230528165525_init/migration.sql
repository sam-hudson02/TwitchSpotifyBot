-- CreateTable
CREATE TABLE "User" (
    "username" TEXT NOT NULL,
    "ban" BOOLEAN NOT NULL DEFAULT false,
    "mod" BOOLEAN NOT NULL DEFAULT false,
    "admin" BOOLEAN NOT NULL DEFAULT false,
    "requests" INTEGER NOT NULL DEFAULT 0,
    "rates" INTEGER NOT NULL DEFAULT 0,
    "ratesGiven" INTEGER NOT NULL DEFAULT 0
);

-- CreateTable
CREATE TABLE "Queue" (
    "id" INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    "name" TEXT NOT NULL,
    "artist" TEXT NOT NULL,
    "requester" TEXT NOT NULL,
    "url" TEXT NOT NULL
);

-- CreateIndex
CREATE UNIQUE INDEX "User_username_key" ON "User"("username");
