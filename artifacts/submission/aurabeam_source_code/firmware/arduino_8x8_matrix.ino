/*
  Firmware Arduino cho LED Matrix 8x8 1588AURGMM noi truc tiep.

  Phan cung:
  - Hang: rowPins[8]
  - Cot:  colPins[8]

  Giao thuc Serial tu Python:
  - BOX:col_start:col_end:row_start:row_end
      Tat vung toi tren matrix
  - BOX:-1:-1:-1:-1
      Xoa vung toi, bat sang toan bo matrix

  Luu y:
  - Day la matrix quet truc tiep, khong dung MAX7219.
  - Do sang "mo" tung LED co the lam bang PWM mem, nhung hien tai
    firmware uu tien dung on/off chinh xac theo toa do de khop Python.
*/

static const uint8_t MATRIX_SIZE = 8;
static const uint8_t SERIAL_BUFFER_SIZE = 48;

// Giu nguyen map chan theo file cu cua ban.
const uint8_t rowPins[MATRIX_SIZE] = {2, 3, 4, 5, 9, 6, 7, 8};
const uint8_t colPins[MATRIX_SIZE] = {10, 11, 12, 13, A2, A3, A4, A5};

// Neu matrix cua ban bi lat ngang, giu true. Neu dung chieu, doi thanh false.
static const bool MIRROR_X = true;

char serialBuffer[SERIAL_BUFFER_SIZE];
uint8_t serialIndex = 0;

bool ledState[MATRIX_SIZE][MATRIX_SIZE];
int boxColStart = -1;
int boxColEnd = -1;
int boxRowStart = -1;
int boxRowEnd = -1;
bool frameDirty = true;

int clampInt(int value, int minimum, int maximum) {
  if (value < minimum) {
    return minimum;
  }
  if (value > maximum) {
    return maximum;
  }
  return value;
}

uint8_t mapColumn(uint8_t col) {
  return MIRROR_X ? static_cast<uint8_t>(MATRIX_SIZE - 1 - col) : col;
}

void clearLatchedCharge() {
  for (uint8_t i = 0; i < MATRIX_SIZE; ++i) {
    digitalWrite(rowPins[i], LOW);
    digitalWrite(colPins[i], HIGH);
  }
}

void rebuildFrame() {
  for (uint8_t row = 0; row < MATRIX_SIZE; ++row) {
    for (uint8_t col = 0; col < MATRIX_SIZE; ++col) {
      ledState[row][col] = true;
    }
  }

  if (boxColStart >= 0 && boxColEnd >= 0 && boxRowStart >= 0 && boxRowEnd >= 0) {
    for (int row = boxRowStart; row <= boxRowEnd; ++row) {
      for (int col = boxColStart; col <= boxColEnd; ++col) {
        uint8_t mappedCol = mapColumn(static_cast<uint8_t>(col));
        ledState[row][mappedCol] = false;
      }
    }
  }

  frameDirty = false;
}

bool parseBoxCommand(const char* payload) {
  int colStart;
  int colEnd;
  int rowStart;
  int rowEnd;

  if (sscanf(payload, "BOX:%d:%d:%d:%d", &colStart, &colEnd, &rowStart, &rowEnd) != 4) {
    return false;
  }

  if (colStart < 0 && colEnd < 0 && rowStart < 0 && rowEnd < 0) {
    boxColStart = -1;
    boxColEnd = -1;
    boxRowStart = -1;
    boxRowEnd = -1;
    frameDirty = true;
    return true;
  }

  colStart = clampInt(colStart, 0, MATRIX_SIZE - 1);
  colEnd = clampInt(colEnd, 0, MATRIX_SIZE - 1);
  rowStart = clampInt(rowStart, 0, MATRIX_SIZE - 1);
  rowEnd = clampInt(rowEnd, 0, MATRIX_SIZE - 1);

  if (colStart > colEnd || rowStart > rowEnd) {
    return false;
  }

  if (boxColStart == colStart && boxColEnd == colEnd && boxRowStart == rowStart && boxRowEnd == rowEnd) {
    return true;
  }

  boxColStart = colStart;
  boxColEnd = colEnd;
  boxRowStart = rowStart;
  boxRowEnd = rowEnd;
  frameDirty = true;
  return true;
}

void processCommand(const char* command) {
  if (command[0] == '\0') {
    return;
  }

  if (strncmp(command, "BOX:", 4) == 0) {
    parseBoxCommand(command);
  }
}

void readSerialCommand() {
  while (Serial.available() > 0) {
    char incoming = static_cast<char>(Serial.read());

    if (incoming == '\r') {
      continue;
    }

    if (incoming == '\n') {
      serialBuffer[serialIndex] = '\0';
      processCommand(serialBuffer);
      serialIndex = 0;
      continue;
    }

    if (serialIndex < (SERIAL_BUFFER_SIZE - 1)) {
      serialBuffer[serialIndex++] = incoming;
    } else {
      serialIndex = 0;
    }
  }
}

void scanMatrix() {
  for (uint8_t row = 0; row < MATRIX_SIZE; ++row) {
    clearLatchedCharge();

    for (uint8_t col = 0; col < MATRIX_SIZE; ++col) {
      digitalWrite(colPins[col], ledState[row][col] ? LOW : HIGH);
    }

    digitalWrite(rowPins[row], HIGH);
    delayMicroseconds(150);
    digitalWrite(rowPins[row], LOW);
    delayMicroseconds(40);
  }
}

void setup() {
  Serial.begin(115200);

  for (uint8_t i = 0; i < MATRIX_SIZE; ++i) {
    pinMode(rowPins[i], OUTPUT);
    pinMode(colPins[i], OUTPUT);
  }

  clearLatchedCharge();
  rebuildFrame();
}

void loop() {
  readSerialCommand();

  if (frameDirty) {
    rebuildFrame();
  }

  scanMatrix();
}
