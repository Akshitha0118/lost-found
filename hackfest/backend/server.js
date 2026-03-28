const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
require('dotenv').config();

const app = express();
const PORT = process.env.PORT || 5000;

// Middleware
const corsOptions = {
  origin: process.env.CORS_ORIGIN || '*',
};
app.use(cors(corsOptions));
app.use(express.json());

// Database Connection
mongoose.connect(process.env.MONGODB_URI || 'mongodb://127.0.0.1:27017/lost-and-found')
  .then(() => console.log('MongoDB connected...'))
  .catch(err => console.log('MongoDB connection error:', err));

// Routes
const itemsRouter = require('./routes/items');
app.use('/api/items', itemsRouter);

// Start Server
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
