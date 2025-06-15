import { pgTable, text, serial, integer, boolean, real } from "drizzle-orm/pg-core";
import { createInsertSchema } from "drizzle-zod";
import { z } from "zod";

export const users = pgTable("users", {
  id: serial("id").primaryKey(),
  username: text("username").notNull().unique(),
  password: text("password").notNull(),
});

export const pathPoints = pgTable("path_points", {
  id: serial("id").primaryKey(),
  x: real("x").notNull(),
  y: real("y").notNull(),
  speed: real("speed").notNull(),
  sequence: integer("sequence").notNull(),
});

export const insertUserSchema = createInsertSchema(users).pick({
  username: true,
  password: true,
});

export const insertPathPointSchema = createInsertSchema(pathPoints).pick({
  x: true,
  y: true,
  speed: true,
  sequence: true,
});

export type InsertUser = z.infer<typeof insertUserSchema>;
export type User = typeof users.$inferSelect;
export type PathPoint = typeof pathPoints.$inferSelect;
export type InsertPathPoint = z.infer<typeof insertPathPointSchema>;

// Client-side types for the path data
export interface PathDataPoint {
  x: number;
  y: number;
  speed: number;
  index: number;
}
