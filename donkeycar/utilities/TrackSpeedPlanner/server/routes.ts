import type { Express } from "express";
import { createServer, type Server } from "http";
import { storage } from "./storage";

export async function registerRoutes(app: Express): Promise<Server> {
  // put application routes here
  // prefix all routes with /api

  // use storage to perform CRUD operations on the storage interface
  // e.g. storage.insertUser(user) or storage.getUserByUsername(username)

  // Shutdown route for clean server exit
  app.post('/api/shutdown', (req, res) => {
    console.log('Shutdown requested via web interface');
    res.json({ message: 'Server shutting down...' });
    
    // Give the response time to send before shutting down
    setTimeout(() => {
      console.log('Server shutting down gracefully');
      process.exit(0);
    }, 1000);
  });

  const httpServer = createServer(app);

  return httpServer;
}
