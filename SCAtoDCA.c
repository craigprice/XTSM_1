/*

Function Description
------------------------
NDG 9/6/12, this routine is part of the timing system for the Gemelke lab rubidium experiment.
It converts a sparse timingstring into a dense control array for a single timing group (AKA output or input board).

Edit History
--------------
The following people have modified the code on the following dates:

NDG 9/6/12  -  Created

Detailed description:
----------------------
This argument takes two arguments:

first a pointer (returnarray) to the first element of a predefined 2D matrix of total size
(number of channels on board)x(number of updates in sequence) note that these parameters can be extracted from
the timingstring itself

second, a pointer (inputarray) to the first element of a 1D byte-array that is the timingstring.  the format is
described below by example:

A simple input timing string (should be passed in as second argument to function below) might look like the following:

54,0,0,0,0,0,0,0,      //Total length of the timingstring in bytes  -  not yet used by dll
2,  		//number of channels in group
4,			//number of bytes used to represent values
4,			//number of bytes used to represent repeat lengths
5,0,0,0,		//number of updates in this sequence
			//begin information for first channel
16,0,0,0,		//number of bytes in timingstring fragment for this channel
200,0,0,0,		//first value
3,0,0,0,		//number of times to repeat first value in this channel's output row 
125,0,0,0,		//second value
2,0,0,0,		//number of times to repeat second value in this channel's output row
			//begin information for second channel
16,0,0,0,		//same format as first (number of bytes in timingstring fragment for this channel)
200,0,0,0,		//first value
4,0,0,0,		//number of times to repeat first value in this channel's output row 
225,0,0,0,		//second value
1,0,0,0			//number of times to repeat second value in this channel's output row

the input string without comments is then:
54,0,0,0,0,0,0,0,2,4,4,5,0,0,0,16,0,0,0,200,0,0,0,3,0,0,0,125,0,0,0,2,0,0,0,16,0,0,0,200,0,0,0,4,0,0,0,225,0,0,0,1,0,0,0

this c-code should be compiled (labwindows/CVI is sufficient) to produce a .dll to execute on the system hosting the output cards.  For the 
rubidium experiment in the Gemelke lab, this should be on the PXI system. The header file SCAtoDCA.h should accompany
this file in the Labwindows project.  

Any calling labview code should set 
	the first parameter as 'return type', type numeric, data-type 8-byte double
	the second parameter as 'returnarray', type Array, data-type Unsigned 32-bit Integer, Dimensions 2, Array format Array Data Pointer
	the third parameter as 'inputarray', type Array, data-type Unsigned 8-bit Integer, Dimensions 1, minimum size <none> Array format Array Data Pointer
the resulting function prototype should then read:  double add1(uint32_t *returnarray, uint8_t *inputarray);

Notes on recompiling:  to recompile, one must delete call library node references to this dll in all open or active (at least)
labview .vis and resave those .vis.  Otherwise, the compiler will complain it does not have access to the file it needs to create.

This routine was clocked at 1.5ms total time on a 10^5 element sequence (10^5 elements in the returnarray) representing 2 edges on a 32-channel dio sequence 10ms long 

End of Comments
----------------
*/
/*	Prototypes of the functions to be exported to the DLL for future use */ 

__declspec(dllexport) double tstodca44(unsigned int *returnarray, unsigned char* inputarray);
__declspec(dllexport) double tstodca24(unsigned short *returnarray, unsigned char* inputarray);
__declspec(dllexport) double tstodca14(unsigned char *returnarray, unsigned char* inputarray);
	
// Functions are defined below	

double tstodca44(unsigned int *returnarray, unsigned char* inputarray)
{
//	the next line reads the first eight bytes as a single 64-bit integer expected to represent the length of the input array
	unsigned long long int* totlen=(unsigned long long int*)(&inputarray[0]);
	unsigned char numchan= inputarray[8];
//  the next byte should tell how many bytes are contained in each value
	unsigned char bytesperval=inputarray[9];
//  the next byte should tell how many bytes are contained in each repeat length
	unsigned char bytesperrep=inputarray[10];
//	the next line reads the next four bytes as a single 32-bit integer expected to represent the number of samples the output array should represent
	unsigned int* outputlen=(unsigned int*)(&inputarray[11]);
// create an index to run through the timing string read operations
	unsigned int ptr=15;
// create an index to run through the output array
	unsigned int ptw=0;
	unsigned int finind=0;
// for each channel's contribution to the timing string, we perform the following
	// first extract the length of its control string (number of updates) as a 4-byte integer
	unsigned int* chanlen;
	unsigned int* val;
	unsigned int* rep;
	unsigned int i=0;
	unsigned int numchanint=(unsigned int) numchan;
	
	// could do some error-checking here to prevent overwrites
	// if (numchanint)*(*outputlen)
	
	// for each channel's timing string
	for (i=0;i<numchanint;i++){
		// reset the column counter
		ptw=0;
		// read the length of the string as a 4-byte integer
		chanlen=(unsigned int*)(&inputarray[ptr]);
		// advance the pointer
		ptr+=4;
		// calculate the pointer value of the last byte in this channel's timingstring
		finind=(*chanlen)+ptr-1;
			if ((bytesperrep == 4) && (bytesperval == 4)) {
				// while the pointer's value is less than this last index
				while (ptr <= finind){
					// initialize pointers for later
					unsigned int* j;
					unsigned int* jlim;
					// read the value as a 4-byte integer
					val=(unsigned int*)(&inputarray[ptr]) ;
					ptr += 4 ;
					// read the # of repetitions of this value as 4-byte integer
					rep=(unsigned int*)(&inputarray[ptr]);
					ptr += 4 ;
					//find the last element that should be updated
					jlim=returnarray+i*(*outputlen)+ptw+*rep;
					// set the next rep number of elements in the output array as the desired value
					for (j=returnarray+i*(*outputlen)+ptw;j<jlim;j++){
						*j=*val;
					}
					ptw+=*rep;
				}

			}
			
	}
	return 1;
}

double tstodca24(unsigned short *returnarray, unsigned char* inputarray)
{
//	the next line reads the first eight bytes as a single 64-bit integer expected to represent the length of the input array
	unsigned long long int* totlen=(unsigned long long int*)(&inputarray[0]);
	unsigned char numchan= inputarray[8];
//  the next byte should tell how many bytes are contained in each value
	unsigned char bytesperval=inputarray[9];
//  the next byte should tell how many bytes are contained in each repeat length
	unsigned char bytesperrep=inputarray[10];
//	the next line reads the next four bytes as a single 32-bit integer expected to represent the number of samples the output array should represent
	unsigned int* outputlen=(unsigned int*)(&inputarray[11]);
// create an index to run through the timing string read operations
	unsigned int ptr=15;
// create an index to run through the output array
	unsigned int ptw=0;
	unsigned int finind=0;
// for each channel's contribution to the timing string, we perform the following
	// first extract the length of its control string (number of updates) as a 4-byte integer
	unsigned int* chanlen;
	unsigned short* val;
	unsigned int* rep;
	unsigned int i=0;
	unsigned int numchanint=(unsigned int) numchan;
	
	// could do some error-checking here to prevent overwrites
	// if (numchanint)*(*outputlen)
	
	// for each channel's timing string
	for (i=0;i<numchanint;i++){
		// reset the column counter
		ptw=0;
		// read the length of the string as a 4-byte integer
		chanlen=(unsigned int*)(&inputarray[ptr]);
		// advance the pointer
		ptr+=4;
		// calculate the pointer value of the last byte in this channel's timingstring
		finind=(*chanlen)+ptr-1;
			if ((bytesperrep == 4) && (bytesperval == 2)) {
				// while the pointer's value is less than this last index
				while (ptr <= finind){
					// initialize pointers for later
					unsigned short* j;
					unsigned short* jlim;
					// read the value as a 2-byte integer
					val=(unsigned short*)(&inputarray[ptr]) ;
					ptr += 2 ;
					// read the # of repetitions of this value as 4-byte integer
					rep=(unsigned int*)(&inputarray[ptr]);
					ptr += 4 ;
					//find the last element that should be updated
					jlim=returnarray+i*(*outputlen)+ptw+*rep;
					// set the next rep number of elements in the output array as the desired value
					for (j=returnarray+i*(*outputlen)+ptw;j<jlim;j++){
						*j=*val;
					}
					ptw+=*rep;
				}

			}
			
	}
	return 1;
}
double tstodca14(unsigned char *returnarray, unsigned char* inputarray)
{
//	the next line reads the first eight bytes as a single 64-bit integer expected to represent the length of the input array
	unsigned long long int* totlen=(unsigned long long int*)(&inputarray[0]);
	unsigned char numchan= inputarray[8];
//  the next byte should tell how many bytes are contained in each value
	unsigned char bytesperval=inputarray[9];
//  the next byte should tell how many bytes are contained in each repeat length
	unsigned char bytesperrep=inputarray[10];
//	the next line reads the next four bytes as a single 32-bit integer expected to represent the number of samples the output array should represent
	unsigned int* outputlen=(unsigned int*)(&inputarray[11]);
// create an index to run through the timing string read operations
	unsigned int ptr=15;
// create an index to run through the output array
	unsigned int ptw=0;
	unsigned int finind=0;
// for each channel's contribution to the timing string, we perform the following
	// first extract the length of its control string (number of updates) as a 4-byte integer
	unsigned int* chanlen;
	unsigned char* val;
	unsigned int* rep;
	unsigned int i=0;
	unsigned int numchanint=(unsigned int) numchan;
	
	// could do some error-checking here to prevent overwrites
	// if (numchanint)*(*outputlen)
	
	// for each channel's timing string
	for (i=0;i<numchanint;i++){
		// reset the column counter
		ptw=0;
		// read the length of the string as a 4-byte integer
		chanlen=(unsigned int*)(&inputarray[ptr]);
		// advance the pointer
		ptr+=4;
		// calculate the pointer value of the last byte in this channel's timingstring
		finind=(*chanlen)+ptr-1;
			if ((bytesperrep == 4) && (bytesperval == 1)) {
				// while the pointer's value is less than this last index
				while (ptr <= finind){
					// initialize pointers for later
					unsigned char* j;
					unsigned char* jlim;
					// read the value as a 1-byte integer
					val=(unsigned char*)(&inputarray[ptr]) ;
					ptr += 1 ;
					// read the # of repetitions of this value as 4-byte integer
					rep=(unsigned int*)(&inputarray[ptr]);
					ptr += 4 ;
					//find the last eleme	nt that should be updated
					jlim=returnarray+i*(*outputlen)+ptw+*rep;
					// set the next rep number of elements in the output array as the desired value
					for (j=returnarray+i*(*outputlen)+ptw;j<jlim;j++){
						*j=*val;
					}
					ptw+=*rep;
				}

			}
			
	}
	return 1;
}
