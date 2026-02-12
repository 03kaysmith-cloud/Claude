require("dotenv").config();
const express = require("express");
const { Client } = require("@notionhq/client");
const path = require("path");

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, "public")));

const notion = new Client({ auth: process.env.NOTION_API_KEY });

// --- Notion API Routes ---

// Search across all connected pages/databases
app.get("/api/search", async (req, res) => {
  try {
    const { query } = req.query;
    const response = await notion.search({
      query: query || "",
      sort: { direction: "descending", timestamp: "last_edited_time" },
    });
    res.json(response);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// List all databases the integration can access
app.get("/api/databases", async (req, res) => {
  try {
    const response = await notion.search({
      filter: { property: "object", value: "database" },
      sort: { direction: "descending", timestamp: "last_edited_time" },
    });
    res.json(response.results);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get a specific database schema + info
app.get("/api/databases/:id", async (req, res) => {
  try {
    const db = await notion.databases.retrieve({ database_id: req.params.id });
    res.json(db);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Query a database (with optional filters)
app.post("/api/databases/:id/query", async (req, res) => {
  try {
    const { filter, sorts, start_cursor, page_size } = req.body;
    const params = { database_id: req.params.id };
    if (filter) params.filter = filter;
    if (sorts) params.sorts = sorts;
    if (start_cursor) params.start_cursor = start_cursor;
    params.page_size = page_size || 50;

    const response = await notion.databases.query(params);
    res.json(response);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get a specific page
app.get("/api/pages/:id", async (req, res) => {
  try {
    const page = await notion.pages.retrieve({ page_id: req.params.id });
    res.json(page);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Get blocks (content) of a page
app.get("/api/blocks/:id/children", async (req, res) => {
  try {
    const blocks = await notion.blocks.children.list({
      block_id: req.params.id,
      page_size: 100,
    });
    res.json(blocks);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Create a page in a database
app.post("/api/pages", async (req, res) => {
  try {
    const { parent_database_id, properties } = req.body;
    const page = await notion.pages.create({
      parent: { database_id: parent_database_id },
      properties,
    });
    res.json(page);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Update a page's properties
app.patch("/api/pages/:id", async (req, res) => {
  try {
    const { properties } = req.body;
    const page = await notion.pages.update({
      page_id: req.params.id,
      properties,
    });
    res.json(page);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// Append blocks to a page
app.post("/api/blocks/:id/children", async (req, res) => {
  try {
    const { children } = req.body;
    const response = await notion.blocks.append({
      block_id: req.params.id,
      children,
    });
    res.json(response);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Notion Chat running at http://localhost:${PORT}`);
});
