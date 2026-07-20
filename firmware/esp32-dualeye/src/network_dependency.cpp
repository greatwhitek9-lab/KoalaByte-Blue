#include <Network.h>

// Arduino 3.x splits Network and WiFi into separate framework libraries.
// This translation unit makes PlatformIO's dependency finder compile Network
// before the integrated Wi-Fi/UDP runtime.
