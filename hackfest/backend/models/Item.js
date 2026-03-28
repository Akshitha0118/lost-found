const mongoose = require('mongoose');

const itemSchema = new mongoose.Schema({
  title: {
    type: String,
    required: true,
    trim: true
  },
  description: {
    type: String,
    required: true
  },
  type: {
    type: String,
    enum: ['LOST', 'FOUND'],
    required: true
  },
  category: {
    type: String,
    default: 'Other'
  },
  location: {
    type: String,
    required: true
  },
  date: {
    type: Date,
    default: Date.now
  },
  status: {
    type: String,
    enum: ['OPEN', 'RESOLVED'],
    default: 'OPEN'
  },
  contactInfo: {
    type: String,
    required: true
  }
}, {
  timestamps: true
});

module.exports = mongoose.model('Item', itemSchema);
