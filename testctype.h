#ifdef _WIN32
void cfun(const unsigned long int, std::size_t, unsigned long int);
void cfun(const double, std::size_t, double);
#elif __APPLE__
#include <string>//CP 2015-01-29
void cfun(const unsigned long int, std::size_t, unsigned long int);
void cfun(const double, std::size_t, double);
#endif