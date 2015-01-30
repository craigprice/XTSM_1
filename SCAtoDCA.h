double tstodca44(unsigned int *returnarray,unsigned char *inputarray);  
double tstodca24(unsigned short *returnarray,unsigned char *inputarray);  
double tstodca14(unsigned char *returnarray,unsigned char *inputarray);  

/*
 * CP compiled this on Pfaffian by opening the developer command prompt in
 * All Programs -> Microsoft Windows SDK v7.1 -> Windows SDK 7.1 Comman Prompt -> Run as Administrator
 * and then used this command on the command prompt:
 * cl /LD C:\\wamp\\www\\compileC\\SCAtoDCA.c /I "C:\\Python27 \include" "C:\\Python27\libs\python27.lib" /link/out:SCAtoDCA64.dll
 * from http://stackoverflow.com/questions/7586504/python-accessing-dll-using-ctypes/13167362#13167362
 * Note:
 * This command which I found from Microsoft did not work:
 * cl /D_USRDLL /D_WINDLL SCAtoDCA.c /link /DLL /OUT:SCAtoDCA64.dll - loading a library into python gave,
 * not a valid Win32 application
 * */
