# MyVoice LoRA - iMessage Data Processing Pipeline

This project extracts and processes iMessage data to create training examples for LoRA fine-tuning of Gemma 3 1B model.

## Features

- 🔍 **iMessage Database Access**: Safely reads from the macOS Messages database
- 📝 **Message Processing**: Extracts text from both `text` and `attributedBody` columns
- 🧹 **Data Filtering**: Removes tapbacks, attachments, and junk messages
- 🔄 **Turn Grouping**: Groups consecutive messages from the same sender into conversation turns
- 📊 **Training Examples**: Creates input/output pairs for model training
- 📈 **Data Statistics**: Provides detailed statistics about the generated dataset

## Prerequisites

### 1. Full Disk Access Permission

You need to grant Full Disk Access to your terminal application:

1. Go to **System Preferences** → **Security & Privacy** → **Privacy**
2. Select **Full Disk Access** from the left sidebar
3. Click the lock icon to make changes
4. Add your terminal application (Terminal.app, iTerm2, etc.)
5. Make sure the checkbox is enabled

### 2. Python Dependencies

Install the required Python packages:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

Run the data processing pipeline:

```bash
python imessage_processor.py
```

This will:
1. Connect to your iMessage database
2. Process all conversations
3. Generate training examples
4. Save results to `training_data.csv`

### Advanced Usage

You can also use the processor programmatically:

```python
from imessage_processor import iMessageProcessor

# Initialize processor
processor = iMessageProcessor()

# Process all conversations
examples = processor.process_all_conversations()

# Save to custom path
processor.save_to_csv(examples, "my_training_data.csv")
```

### Testing with Small Datasets

For testing purposes, you can limit the date range to process only recent messages:

1. **Edit `config.py`** and set `DAYS_BACK = 1` to process only the last 24 hours
2. **Run the processor**: `python imessage_processor.py`
3. **Check the output**: Review the generated `training_data.csv` file
4. **Adjust as needed**: Increase `DAYS_BACK` to include more historical data

This is especially useful for:
- Testing the pipeline before processing your entire message history
- Creating smaller datasets for initial model training
- Debugging any issues with the data processing

## Output Format

The pipeline generates a CSV file with two columns:

- **input**: The previous turn's content (or `[CONVERSATION_STARTER]` if it's the first turn)
- **output**: Your response in that conversation

Example:
```csv
input,output
[CONVERSATION_STARTER],Hey! How are you doing?
Hey! How are you doing?,I'm doing great, thanks for asking!
I'm doing great, thanks for asking!,That's awesome to hear!
```

## Data Processing Pipeline

### 1. Database Connection
- Connects to `~/Library/Messages/chat.db`
- Uses read-only mode for safety
- Handles permission errors gracefully

### 2. Message Extraction
- Extracts text from both `text` and `attributedBody` columns
- Converts Messages.app timestamps to Python datetime
- Filters out empty or invalid messages

### 3. Junk Filtering
Removes the following types of messages:
- Tapbacks ("Liked", "Laughed at", etc.)
- Messages with only attachments
- Very short messages (< 2 characters)
- Messages that are just placeholders

### 4. Turn Grouping
- Groups consecutive messages from the same sender
- Maintains chronological order
- Creates conversation turns for better context

### 5. Training Example Generation
- For each of your turns, creates a training example
- Input: Previous turn from the other person
- Output: Your response
- Handles conversation starters appropriately

## Configuration

You can customize the processing by modifying `config.py`:

- `DAYS_BACK`: Number of days back in history to process (set to `None` for all history)
- `MIN_MESSAGE_LENGTH`: Minimum characters for valid messages
- `MAX_MESSAGE_LENGTH`: Maximum characters for messages
- `MAX_TURN_GAP_SECONDS`: Maximum gap to group messages in same turn
- `CONVERSATION_STARTER_TOKEN`: Token for conversation starters

### Date Range Examples

```python
# Process only last 24 hours (for testing)
DAYS_BACK = 1

# Process last week
DAYS_BACK = 7

# Process last month
DAYS_BACK = 30

# Process last year
DAYS_BACK = 365

# Process all history (default)
DAYS_BACK = None
```

## Troubleshooting

### Permission Denied
If you get permission errors:
1. Make sure Full Disk Access is enabled for your terminal
2. Restart your terminal application
3. Try running the script again

### No Messages Found
If no messages are processed:
1. Check that you have iMessages in your database
2. Verify the database path is correct
3. Check the logs for specific error messages

### Empty Output
If the CSV file is empty:
1. Check that you have conversations where you sent messages
2. Verify that messages aren't being filtered out as junk
3. Look at the logs for processing statistics

## Security and Privacy

- **Read-only access**: The script only reads from the database, never writes
- **Local processing**: All data processing happens locally on your machine
- **No data transmission**: No data is sent to external servers
- **Optional logging**: Logs can be disabled or configured for privacy

## File Structure

```
myvoice_lora/
├── imessage_processor.py    # Main processing script
├── config.py               # Configuration settings
├── requirements.txt        # Python dependencies
├── README.md              # This file
└── training_data.csv      # Generated training data (after running)
```

## Next Steps

After generating your training data:

1. **Review the data**: Check the generated CSV file for quality
2. **Clean if needed**: Remove any unwanted examples manually
3. **Prepare for training**: Use the data with your LoRA training pipeline
4. **Fine-tune**: Train your Gemma 3 1B model with the generated examples

## Contributing

Feel free to submit issues and enhancement requests!

## License

This project is for personal use. Please respect privacy and data protection guidelines. 