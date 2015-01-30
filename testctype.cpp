#include "testctype.h"
//CP 2015-01-29
#ifdef _WIN32
#include "stdAfx.h"
#endif
#include "limits.h"
#include "float.h"
#define DLLEXPORT extern "C" __declspec(dllexport)

DLLEXPORT void repasuint8(unsigned long int *indatav, unsigned long int indatalength, unsigned long int *ptrs, const unsigned char firstelm, unsigned char *outdatav, const unsigned long int outlength) 
{
	// use provided index pointers to get memory pointers
	unsigned long int *ptr[8];
    unsigned long int *fptr[8];
	ptr[0] = &(indatav[ptrs[0]]); 
	for (int i=1;i<8;i++) 
	{ 
		ptr[i] = &(indatav[ptrs[i]]); 
		fptr[i-1] = ptr[i]-1; 
	}
	fptr[7]=&(indatav[indatalength-1]);
	outdatav[0]=firstelm;
	// step through bit-flipping algorithm
	int j=1;
	bool active = true;
	unsigned long int min;
	unsigned char hits;
	while (j < outlength) 
	{
		hits = ((unsigned char)1);
		min = ULONG_MAX;
		// find which ptrs point to minimum value
		for (int i=0;i<8;i++)
		{
			// if this bit is finished, skip
			if (ptr[i]>fptr[i]) {continue;}
			// if we found a new minimum, reset previous bits and min value
			if (*(ptr[i]) < min) 
			{
				min=*(ptr[i]);
				hits = (((unsigned char)1) << i);
				continue;
			}
			// if this points to minimum time as well, set as hit
			if (*(ptr[i]) == min) 
			{
				hits |= (((unsigned char)1) << i);
			}
		}
		// flip bits at hits
		outdatav[j]=outdatav[j-1] ^ hits;
		j++;
		// advance ptrs where hit
		for (int i=0;i<8;i++)
		{
			if ((hits >> i)%2) {ptr[i]=ptr[i]+1;}
		}
	}
}

DLLEXPORT void repasuint32(unsigned long int *indatav, unsigned long int indatalength, unsigned long int *ptrs, const unsigned long int firstelm, unsigned long int *outdatav, const unsigned long int outlength) 
{
	// use provided index pointers to get memory pointers
	unsigned long int *ptr[32];
    unsigned long int *fptr[32];
	ptr[0] = &(indatav[ptrs[0]]); 
	for (int i=1;i<32;i++) 
	{ 
		ptr[i] = &(indatav[ptrs[i]]); 
		fptr[i-1] = ptr[i]-1; 
	}
	fptr[31]=&(indatav[indatalength-1]);
	outdatav[0]=firstelm;
	// step through bit-flipping algorithm
	int j=1;
	bool active = true;
	unsigned long int min;
	unsigned long int hits;
	while (j < outlength) 
	{
		hits = ((unsigned long int)1);
		min = ULONG_MAX;
		// find which ptrs point to minimum value
		for (int i=0;i<32;i++)
		{
			// if this bit is finished, skip
			if (ptr[i]>fptr[i]) {continue;}
			// if we found a new minimum, reset previous bits and min value
			if (*(ptr[i]) < min) 
			{
				min=*(ptr[i]);
				hits = (((unsigned long int)1) << i);
				continue;
			}
			// if this points to minimum time as well, set as hit
			if (*(ptr[i]) == min) 
			{
				hits |= (((unsigned long int)1) << i);
			}
		}
		// flip bits at hits
		outdatav[j]=outdatav[j-1] ^ hits;
		j++;
		// advance ptrs where hit
		for (int i=0;i<32;i++)
		{
			if ((hits >> i)%2) {ptr[i]=ptr[i]+1;}
		}
	}
}



DLLEXPORT void repasuint8dev(unsigned long int *indatav, unsigned long int indatalength, unsigned long int *ptrs, const unsigned char firstelm, unsigned char *outdatav, const unsigned long int outlength) 
{
	// use provided index pointers to get memory pointers
	unsigned long int *ptr[8];
    unsigned long int *fptr[8];
	ptr[0] = &(indatav[ptrs[0]]); 
	for (int i=1;i<8;i++) 
	{ 
		ptr[i] = &(indatav[ptrs[i]]); 
		fptr[i-1] = ptr[i]-1; 
	}
	fptr[7]=&(indatav[indatalength-1]);
	outdatav[0]=firstelm;
	// step through bit-flipping algorithm
	int j=1;
	unsigned long int min;
	unsigned char hits;
	while (j < outlength) 
	{
		min = ULONG_MAX;
		// find which ptrs point to minimum value
		for (int i=0;i<8;i++)
		{
			// if this bit is finished, skip
			if (ptr[i]>fptr[i]) 
			{
				continue;
			}
			// if we found a new minimum, reset previous bits and min value
			if (*(ptr[i]) < min) 
			{
				min=*(ptr[i]);
				for (int k=i-1; k>=0;k--) 
				{
					if (hits & (1 << k)) {ptr[k]--;}
				} 
				hits = (1 << i);
				ptr[i]++;
				continue;
			}
			// if this points to minimum time as well, set as hit
			if (*(ptr[i]) == min) 
			{
				hits |= (1 << i);
				ptr[i]++;
			}
		}
		// flip bits at hits
		outdatav[j]=outdatav[j-1] ^ hits;
		j++;
	}
}
DLLEXPORT void repasuint8pulse(unsigned long int *indatav, unsigned long int indatalength, unsigned long int *ptrs, const unsigned char firstelm, unsigned char *outdatav, const unsigned long int outlength) 
{
	// use provided index pointers to get memory pointers
	unsigned long int *ptr[8];
    unsigned long int *fptr[8];
	ptr[0] = &(indatav[ptrs[0]]); 
	for (int i=1;i<8;i++) 
	{ 
		ptr[i] = &(indatav[ptrs[i]]); 
		fptr[i-1] = ptr[i]-1; 
	}
	fptr[7]=&(indatav[indatalength-1]);
	outdatav[0]=firstelm;
	// step through bit-flipping algorithm
	int j=1;
	unsigned long int min;
	unsigned char hits;
	while (j < outlength) 
	{
		min = ULONG_MAX;
		// find which ptrs point to minimum value
		for (int i=0;i<8;i++)
		{
			// if this bit is finished, skip
			if (ptr[i]>fptr[i]) 
			{
				continue;
			}
			// if we found a new minimum, reset previous bits and min value
			if (*(ptr[i]) < min) 
			{
				min=*(ptr[i]);
				for (int k=i-1; k>=0;k--) 
				{
					if (hits & (128 >> k)) {ptr[k]--;}
				} 
				hits = (128 >> i);
				ptr[i]++;
				continue;
			}
			// if this points to minimum time as well, set as hit
			if (*(ptr[i]) == min) 
			{
				hits |= (128 >> i);
				ptr[i]++;
			}
		}
		// raise bits at hits
		outdatav[j]=hits;
		j++;
	}
}
DLLEXPORT void repasuint8pulsedev0(unsigned long int *indatav, unsigned long int indatalength, unsigned long int *ptrs, const unsigned char firstelm, unsigned char *outdatav, const unsigned long int outlength) 
{
	//this tries to speed up conversion by starting from both ends of each timingstring segment (most channels have edges at both start and end of sequence), and deactivates pointers which have finished scanning
	//as they complete - for sequences with a small number of very active channels, this should be faster - though it does not yet appear significantly faster (~30% for 2/8 channels dense with data)

	// use provided index pointers to get memory pointers
	unsigned long int *ptr[8];
    unsigned long int *fptr[8];
	ptr[0] = &(indatav[ptrs[0]]);
	unsigned char* o_outdatav=outdatav;
	for (int i=1;i<8;i++) 
	{ 
		ptr[i] = &(indatav[ptrs[i]]); 
		fptr[i-1] = ptr[i]-1; 
	}
	fptr[7]=&(indatav[indatalength-1]);
	unsigned char* outdatavf=&(outdatav[outlength-2]);  //pointer to last element in output array
	outdatav[0]=firstelm;
	outdatav++;
	// step through bit-flipping algorithm, incrementing ptrs and decrementing fptrs until they meet
	unsigned long int min;
	unsigned long int max;
	unsigned char hits;
	unsigned char fhits;
	unsigned char ptrind[8];  // current ordering of active pointers
	for (unsigned char i=0;i<8;i++) 
	{ 
		ptrind[i] = 128 >> i; 
	}
	int nptr=8;  // current number of active pointers
	while (outdatav<=outdatavf)
	{
		for (int i=0;i<nptr;i++)
		{
			// if this bit is finished, deactivate by shuffling ptrs
			if (ptr[i]>fptr[i])
			{
				for (int j=i;j<(nptr-1);j++)
				{
					ptr[j]=ptr[j+1];
					fptr[j]=fptr[j+1];
					ptrind[j]=ptrind[j+1];
				}
				nptr--;
				i--;
			}
		}
		// find minimum pointed by ptrs
		min = *(ptr[0]);
		for (int i=1;i<nptr;i++)
		{
			if (*(ptr[i]) < min)
			{
				min=*(ptr[i]);
			}
		}
		max=*(fptr[0]);
		for (int i=1;i<nptr;i++)
		{
			if (*(fptr[i]) > max)
			{
				max=*(fptr[i]);
			}
		}
		hits=0;
		fhits=0;
		// find which ptrs point to min and max values
		for (int i=0;i<nptr;i++)
		{
			// if this points to minimum time, set as hit
			if (*(ptr[i]) == min) 
			{
				hits |= ptrind[i];
				ptr[i]++;
			}
			// if this points to maximum time as well, set as hit
			if (*(fptr[i]) == max) 
			{
				fhits |= ptrind[i];
				fptr[i]--;
			}
		}
		// flip bits at hits
		*outdatav=hits;
		outdatav++;
		// flip bits at hits
		*outdatavf=fhits;
		outdatavf--;
	}
	outdatav=o_outdatav;
	return;
}

DLLEXPORT void repasuint8pulsedev(unsigned long int *indatav, unsigned long int indatalength, unsigned long int *ptrs, const unsigned char firstelm, unsigned char *outdatav, const unsigned long int outlength) 
{
	//this tries to speed up conversion by starting from both ends of each timingstring segment (most channels have edges at both start and end of sequence), and deactivates pointers which have finished scanning
	//as they complete - for sequences with a small number of very active channels, this should be faster - though it does not yet appear significantly faster (~20% for 2/8 channels dense with data)

	// use provided index pointers to get memory pointers
	unsigned long int *ptr[8];
    unsigned long int *fptr[8];
	ptr[0] = &(indatav[ptrs[0]]);
	unsigned char* o_outdatav=outdatav;
	for (int i=1;i<8;i++) 
	{ 
		ptr[i] = &(indatav[ptrs[i]]); 
		fptr[i-1] = ptr[i]-1; 
	}
	fptr[7]=&(indatav[indatalength-1]);
	unsigned char* outdatavf=&(outdatav[outlength-2]);  //pointer to last element in output array
	outdatav[0]=firstelm;
	outdatav++;
	// step through bit-flipping algorithm, incrementing ptrs and decrementing fptrs until they meet
	unsigned long int min;
	unsigned long int max;
	unsigned char hits;
	unsigned char fhits;
	unsigned char ptrind[8];  // current ordering of active pointers
	for (unsigned char i=0;i<8;i++) 
	{ 
		ptrind[i] = 128 >> i; 
	}
	int nptr=8;  // current number of active pointers
	while (nptr>2)
	{
		for (int i=0;i<nptr;i++)
		{
			// if this bit is finished, deactivate by shuffling ptrs
			if (ptr[i]>fptr[i])
			{
				for (int j=i;j<(nptr-1);j++)
				{
					ptr[j]=ptr[j+1];
					fptr[j]=fptr[j+1];
					ptrind[j]=ptrind[j+1];
				}
				nptr--;
				i--;
			}
		}
		// find minimum pointed by ptrs
		min = *(ptr[0]);
		for (int i=1;i<nptr;i++)
		{
			if (*(ptr[i]) < min)
			{
				min=*(ptr[i]);
			}
		}
		max=*(fptr[0]);
		for (int i=1;i<nptr;i++)
		{
			if (*(fptr[i]) > max)
			{
				max=*(fptr[i]);
			}
		}
		hits=0;
		fhits=0;
		// find which ptrs point to min and max values
		for (int i=0;i<nptr;i++)
		{
			// if this points to minimum time, set as hit
			if (*(ptr[i]) == min) 
			{
				hits |= ptrind[i];
				ptr[i]++;
			}
			// if this points to maximum time as well, set as hit
			if (*(fptr[i]) == max) 
			{
				fhits |= ptrind[i];
				fptr[i]--;
			}
		}
		// flip bits at hits
		*outdatav=hits;
		outdatav++;
		// flip bits at hits
		*outdatavf=fhits;
		outdatavf--;
	}
	unsigned char eq=(ptrind[0]|ptrind[1]);
	while (nptr>1)
	{

		if (ptr[0]>fptr[0]) { ptr[0]=ptr[1]; ptrind[0]=ptrind[1]; nptr--;}
		if (ptr[1]>fptr[1]) { nptr--;}
		if (*ptr[0] == *ptr[1]) {*outdatav=eq; ptr[0]++; ptr[1]++;	} else
		if (*ptr[0] <  *ptr[1]) {*outdatav=ptrind[0];	 ptr[0]++;	} else 
								{*outdatav=ptrind[1];	 ptr[1]++;	}
		outdatav++;
	}
	outdatav--;
	while (outdatav<=outdatavf)
	{
		*outdatav=ptrind[0];
		outdatav++;
	}
	outdatav=o_outdatav;
	return;
}


DLLEXPORT void repasuint8pulsedev2(unsigned long int *indatav, unsigned long int indatalength, unsigned long int *ptrs, const unsigned char firstelm, unsigned char *outdatav, const unsigned long int outlength) 
{
	// use provided index pointers to get memory pointers
	unsigned long int *ptr[8];
    unsigned long int *fptr[8];
	ptr[0] = &(indatav[ptrs[0]]); 
	for (int i=1;i<8;i++) 
	{ 
		ptr[i] = &(indatav[ptrs[i]]); 
		fptr[i-1] = ptr[i]-1; 
	}
	fptr[7]=&(indatav[indatalength-1]);
	outdatav[0]=firstelm;
	// step through bit-flipping algorithm
	int j=1;
	unsigned long int min;
	unsigned char hits;
	while (j < outlength) 
	{
		min = ULONG_MAX;
		// find which ptrs point to minimum value
		for (int i=0;i<8;i++)
		{
			// if this bit is finished, skip
			if (ptr[i]>fptr[i]) 
			{
				continue;
			}
			// if we found a new minimum, reset previous bits and min value
			if (*(ptr[i]) < min) 
			{
				min=*(ptr[i]);
				for (int k=i-1; k>=0;k--) 
				{
					if (hits & (1 << k)) {ptr[k]--;}
				} 
				hits = (1 << i);
				ptr[i]++;
				continue;
			}
			// if this points to minimum time as well, set as hit
			if (*(ptr[i]) == min) 
			{
				hits |= (1 << i);
				ptr[i]++;
			}
		}
		// flip bits at hits
		outdatav[j]=hits;
		j++;
	}
}

DLLEXPORT void repasuint32pulse(unsigned long int *indatav, unsigned long int indatalength, unsigned long int *ptrs, const unsigned long int firstelm, unsigned long int *outdatav, const unsigned long int outlength) 
{
	// use provided index pointers to get memory pointers
	unsigned long int *ptr[32];
    unsigned long int *fptr[32];
	ptr[0] = &(indatav[ptrs[0]]); 
	for (int i=1;i<32;i++) 
	{ 
		ptr[i] = &(indatav[ptrs[i]]); 
		fptr[i-1] = ptr[i]-1; 
	}
	fptr[31]=&(indatav[indatalength-1]);
	outdatav[0]=firstelm;
	// step through bit-flipping algorithm
	int j=1;
	unsigned long int min;
	unsigned long int hits;
	while (j < outlength) 
	{
		min = ULONG_MAX;
		// find which ptrs point to minimum value
		for (int i=0;i<32;i++)
		{
			// if this bit is finished, skip
			if (ptr[i]>fptr[i]) 
			{
				continue;
			}
			// if we found a new minimum, reset previous bits and min value
			if (*(ptr[i]) < min)  
			{
				min=*(ptr[i]);
				for (int k=i-1; k>=0;k--) 
				{
					if (hits & (2147483648 >> k)) {ptr[k]--;}
				} 
				hits = (2147483648 >> i);
				ptr[i]++;
				continue;
			}
			// if this points to minimum time as well, set as hit
			if (*(ptr[i]) == min) 
			{
				hits |= (2147483648 >> i);
				ptr[i]++;
			}
		}
		// raise bits at hits
		outdatav[j]=hits;
		j++;
	}
}

DLLEXPORT void merge_sorted_arrays3(long double** addrs, unsigned int arrnum, unsigned long int* lens) 
{ 
	// this function merges an indefinite number of pre-sorted arrays, discarding duplicates
	// index addrs as [which-array index][element thereof]
	
	int outind=arrnum-1; // the index of the output pointer
	long double* o_outptr=addrs[outind]; // the original location of the output pointer
	long double dblmax=DBL_MAX; // the maximum value a double float can have
	long double* minptr=&dblmax;  // a ptr to the maximum value a double float can have
	long double* f_addrs[80];  // final resting points for pointers
	for (int i=0; i<(arrnum-1); i++) 
	{
		f_addrs[i]=addrs[i]+lens[i];
	}

	while (arrnum>2){ // while there are elements in more than one array left to sort
		// deactivate any active arrays where the pointer is done by removing ptr from stack
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (addrs[i]==f_addrs[i]) 
			{
				for (int f=i; f<(arrnum-1);f++) 
				{
					addrs[f]=addrs[f+1];
					//lens[f]=lens[f+1];
					f_addrs[f]=f_addrs[f+1];
				}  // shuffle all higher ptrs down in ptr array
				arrnum--; 
			}
		}
		// find the minimum value at the currently pointed-to location in each array 
		minptr=&dblmax;
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (*(addrs[i]) < *minptr) { minptr = addrs[i]; }
		}
		// for each array currently pointing to the minimum value, increment its ptr
		for (int i=0; i<(arrnum-1); i++)
		{
			if (*(addrs[i]) == *minptr )  
			{ 
				addrs[i]+=1;
			}
		}
		// add the minimum value to the output array, advance its pointer
		*addrs[outind]=*minptr;
		addrs[outind]+=1;
	}
	while (addrs[0]<f_addrs[0]) // the remainder of the last array just needs to be copied
	{
		*addrs[outind]=*addrs[0];
		addrs[outind]+=1;
		addrs[0]+=1;
	}

	lens[outind]=addrs[outind]-o_outptr+1;  // sets the last element of the array-length array to the total number in the output array.
	return;
}
DLLEXPORT void merge_sorted_float64(long double** addrs, unsigned int arrnum, unsigned long int* lens) 
{ 
	// this function merges an indefinite number of pre-sorted arrays, discarding duplicates, including within an array
	// index addrs as [which-array index][element thereof]
	
	// note arrnum should be 1 + (the number of input arrays to be merged).  

	int outind=arrnum-1; // the index of the output pointer
	long double* o_outptr=addrs[outind]; // the original location of the output pointer
	long double dblmax=DBL_MAX; // the maximum value a double float can have
	long double* minptr=&dblmax;  // a ptr to the maximum value a double float can have
	long double* f_addrs[80];  // final resting points for pointers
	for (int i=0; i<(arrnum-1); i++) 
	{
		f_addrs[i]=addrs[i]+lens[i];
	}
	long double* o_addrs[80];  // original pointers
	for (int i=0; i<(arrnum-1); i++) 
	{
		o_addrs[i]=addrs[i];
	}
	*addrs[outind]=dblmax;  // set the first output element to maximum dbl value
	addrs[outind]+=1;  // advance pointer
	while (arrnum>2){ // while there are elements in more than one array left to sort
		// find the minimum value at the currently pointed-to location in each array 
		minptr=&dblmax;
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (*(addrs[i]) < *minptr) { minptr = addrs[i]; }
		}
		// for each array currently pointing to the minimum value, increment its ptr
		for (int i=0; i<(arrnum-1); i++)
		{
			if (*(addrs[i]) == *minptr )  
			{ 
				addrs[i]+=1;
			}
		}
		// if new, add the minimum value to the output array, advance its pointer
		if (*(addrs[outind]-1)!=*minptr)  
			{
				*addrs[outind]=*minptr;
				addrs[outind]+=1;
			}
		// deactivate any active arrays where the pointer is done by removing ptr from stack
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (addrs[i]==f_addrs[i]) 
			{
				for (int f=i; f<(arrnum-1);f++) 
				{
					addrs[f]=addrs[f+1];
					f_addrs[f]=f_addrs[f+1];
				}  // shuffle all higher ptrs down in ptr array
				arrnum--;
				i--;    // need to look at this index again on next iteration
			}
		}
	}  // if there is an array left, the remainder of the last array just needs to be copied
	if (arrnum==2)
	{
		while (addrs[0]<f_addrs[0]) 
			{
				if (*(addrs[outind]-1)!=*addrs[0])
					{
						*addrs[outind]=*addrs[0];
						addrs[outind]+=1;
					}
				addrs[0]+=1;
			}
	}

	lens[outind]=addrs[outind]-o_outptr;  // sets the last element of the array-length array to the total number in the output array.
	addrs[outind]=o_outptr;  // resets pointer to original location
	for (int i=0; i<(arrnum-1); i++) 
	{
		addrs[i]=o_addrs[i];
	}
	return;
}
DLLEXPORT void merge_sorted_float32(float** addrs, unsigned int arrnum, unsigned long int* lens) 
{ 
	// this function merges an indefinite number of pre-sorted arrays, discarding duplicates, including within an array
	// index addrs as [which-array index][element thereof]
	
	// note arrnum should be 1 + (the number of input arrays to be merged).  

	int outind=arrnum-1; // the index of the output pointer
	float* o_outptr=addrs[outind]; // the original location of the output pointer
	float dblmax=FLT_MAX; // the maximum value a double float can have
	float* minptr=&dblmax;  // a ptr to the maximum value a double float can have
	float* f_addrs[80];  // final resting points for pointers
	for (int i=0; i<(arrnum-1); i++) 
	{
		f_addrs[i]=addrs[i]+lens[i];
	}
	float* o_addrs[80];  // original pointers
	for (int i=0; i<(arrnum-1); i++) 
	{
		o_addrs[i]=addrs[i];
	}
	*addrs[outind]=dblmax;  // set the first output element to maximum dbl value
	addrs[outind]+=1;  // advance pointer
	while (arrnum>2){ // while there are elements in more than one array left to sort
		// find the minimum value at the currently pointed-to location in each array 
		minptr=&dblmax;
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (*(addrs[i]) < *minptr) { minptr = addrs[i]; }
		}
		// for each array currently pointing to the minimum value, increment its ptr
		for (int i=0; i<(arrnum-1); i++)
		{
			if (*(addrs[i]) == *minptr )  
			{ 
				addrs[i]+=1;
			}
		}
		// if new, add the minimum value to the output array, advance its pointer
		if (*(addrs[outind]-1)!=*minptr)  
			{
				*addrs[outind]=*minptr;
				addrs[outind]+=1;
			}
		// deactivate any active arrays where the pointer is done by removing ptr from stack
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (addrs[i]==f_addrs[i]) 
			{
				for (int f=i; f<(arrnum-1);f++) 
				{
					addrs[f]=addrs[f+1];
					f_addrs[f]=f_addrs[f+1];
				}  // shuffle all higher ptrs down in ptr array
				arrnum--;
				i--;    // need to look at this index again on next iteration
			}
		}
	}  // if there is an array left, the remainder of the last array just needs to be copied
	if (arrnum==2)
	{
		while (addrs[0]<f_addrs[0]) 
			{
				if (*(addrs[outind]-1)!=*addrs[0])
					{
						*addrs[outind]=*addrs[0];
						addrs[outind]+=1;
					}
				addrs[0]+=1;
			}
	}

	lens[outind]=addrs[outind]-o_outptr;  // sets the last element of the array-length array to the total number in the output array.
	addrs[outind]=o_outptr;  // resets pointer to original location
	for (int i=0; i<(arrnum-1); i++) 
	{
		addrs[i]=o_addrs[i];
	}
	return;
}
DLLEXPORT void merge_sorted_track_indices_float64(long double** addrs, unsigned int arrnum, unsigned long int* lens) 
{ 
	// this function merges an indefinite number of pre-sorted arrays, discarding duplicates, including within an array
	// this version keeps track of indices of a given array's contributions to the output array by overwriting the input array's values with indices

	// index addrs as [which-array index][element thereof]	
	// note arrnum should be 1 + (the number of input arrays to be merged).  

	int outind=arrnum-1; // the index of the output pointer
	long double* o_outptr=addrs[outind]; // the original location of the output pointer
	long double min=DBL_MAX;  // the maximum value a double float can have
	long double* f_addrs[80];  // final resting points for pointers
	for (int i=0; i<(arrnum-1); i++) 
	{
		f_addrs[i]=addrs[i]+lens[i];
	}
	long double* o_addrs[80];  // original pointers
	for (int i=0; i<(arrnum-1); i++) 
	{
		o_addrs[i]=addrs[i];
	}
	*addrs[outind]=DBL_MAX;  // set the first output element to maximum dbl value
	addrs[outind]+=1;  // advance pointer
	while (arrnum>2){ // while there are elements in more than one array left to sort
		// find the minimum value at the currently pointed-to location in each array 
		min=DBL_MAX;
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (*(addrs[i]) < min) { min = *addrs[i]; }
		}
		// for each array currently pointing to the minimum value, increment its ptr and overwrite its value with the current output index
		for (int i=0; i<(arrnum-1); i++)
		{
			if (*(addrs[i]) == min )  
			{ 
				*(addrs[i])=addrs[outind]-o_outptr-1;  // record the index for this channel's contribution at this step
				addrs[i]+=1;
			}
		}
		// if new, add the minimum value to the output array, advance its pointer
		if (*(addrs[outind]-1)!=min)  
			{
				*addrs[outind]=min;
				addrs[outind]+=1;
			}
		// deactivate any active arrays where the pointer is done by removing ptr from stack
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (addrs[i]==f_addrs[i]) 
			{
				for (int f=i; f<(arrnum-1);f++) 
				{
					addrs[f]=addrs[f+1];
					f_addrs[f]=f_addrs[f+1];
				}  // shuffle all higher ptrs down in ptr array
				arrnum--;
				i--;    // need to look at this index again on next iteration
			}
		}
	}  // if there is an array left, the remainder of the last array just needs to be copied
	if (arrnum==2)
	{
		while (addrs[0]<f_addrs[0]) 
			{
				if (*(addrs[outind]-1)!=*addrs[0])
					{
						*addrs[outind]=*addrs[0];  
						*(addrs[0])=addrs[outind]-o_outptr-1; // since we are writing to the output, we also need to write indices to the input array as we go
						addrs[0]++;
						addrs[outind]+=1;
					}
				addrs[0]+=1;
			}
	}

	lens[outind]=addrs[outind]-o_outptr;  // sets the last element of the array-length array to the total number in the output array.
	addrs[outind]=o_outptr;  // resets pointer to original location
	for (int i=0; i<(arrnum-1); i++) 
	{
		addrs[i]=o_addrs[i];
	}
	return;
}
DLLEXPORT void merge_sorted_track_indices_float32(float** addrs, unsigned int arrnum, unsigned long int* lens) 
{ 
	// this function merges an indefinite number of pre-sorted arrays, discarding duplicates, including within an array
	// this version keeps track of indices of a given array's contributions to the output array by overwriting the input array's values with indices

	// index addrs as [which-array index][element thereof]	
	// note arrnum should be 1 + (the number of input arrays to be merged).  

	int outind=arrnum-1; // the index of the output pointer
	float* o_outptr=addrs[outind]; // the original location of the output pointer
	float min=FLT_MAX;  // the maximum value a double float can have
	float* f_addrs[80];  // final resting points for pointers
	for (int i=0; i<(arrnum-1); i++) 
	{
		f_addrs[i]=addrs[i]+lens[i];
	}
	float* o_addrs[80];  // original pointers
	for (int i=0; i<(arrnum-1); i++) 
	{
		o_addrs[i]=addrs[i];
	}
	*addrs[outind]=FLT_MAX;  // set the first output element to maximum dbl value
	addrs[outind]+=1;  // advance pointer
	while (arrnum>2){ // while there are elements in more than one array left to sort
		// find the minimum value at the currently pointed-to location in each array 
		min=FLT_MAX;
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (*(addrs[i]) < min) { min = *addrs[i]; }
		}
		// for each array currently pointing to the minimum value, increment its ptr and overwrite its value with the current output index
		for (int i=0; i<(arrnum-1); i++)
		{
			if (*(addrs[i]) == min )  
			{ 
				*(addrs[i])=addrs[outind]-o_outptr-1;  // record the index for this channel's contribution at this step
				addrs[i]+=1;
			}
		}
		// if new, add the minimum value to the output array, advance its pointer
		if (*(addrs[outind]-1)!=min)  
			{
				*addrs[outind]=min;
				addrs[outind]+=1;
			}
		// deactivate any active arrays where the pointer is done by removing ptr from stack
		for (int i=0; i<(arrnum-1); i++) 
		{
			if (addrs[i]==f_addrs[i]) 
			{
				for (int f=i; f<(arrnum-1);f++) 
				{
					addrs[f]=addrs[f+1];
					f_addrs[f]=f_addrs[f+1];
				}  // shuffle all higher ptrs down in ptr array
				arrnum--;
				i--;    // need to look at this index again on next iteration
			}
		}
	}  // if there is an array left, the remainder of the last array just needs to be copied
	if (arrnum==2)
	{
		while (addrs[0]<f_addrs[0]) 
			{
				if (*(addrs[outind]-1)!=*addrs[0])
					{
						*addrs[outind]=*addrs[0];  
						*(addrs[0])=addrs[outind]-o_outptr-1; // since we are writing to the output, we also need to write indices to the input array as we go
						addrs[0]++;
						addrs[outind]+=1;
					}
				addrs[0]+=1;
			}
	}

	lens[outind]=addrs[outind]-o_outptr;  // sets the last element of the array-length array to the total number in the output array.
	addrs[outind]=o_outptr;  // resets pointer to original location
	for (int i=0; i<(arrnum-1); i++) 
	{
		addrs[i]=o_addrs[i];
	}
	return;
}
