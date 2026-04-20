/****************************************************************************
; * 																		
; * 	File		:	w32_dx.h                                           
; * 																	    
; * 	Description :	Win32 Direct X Detection
; * 				                                                        
; * 	Copyright © Realtech VR 1995 - 2003 - http://www.v3x.net									
; * 																		
; * 	Permission to use, copy, modify, distribute and sell this software	
; * 	and its documentation for any purpose is hereby granted without fee,
; * 	provided that the above copyright notice appear in all copies and	
; * 	that both that copyright notice and this permission notice appear	
; * 	in supporting documentation.  Realtech makes no representations 	
; * 	about the suitability of this software for any purpose. 			
; * 	It is provided "as is" without express or implied warranty. 		
; * 																		
; ***************************************************************************/

#ifndef __W32_DX_HH
#define __W32_DX_HH


__inline int __SYS_DXTRACE(const char *file, int line, HRESULT hr)
{	
	if (hr)
	{		
		char tmp[1024];
		sprintf(tmp, "%s(%d) : 0h%08X\n", file, line, hr);
		OutputDebugString(tmp);
#ifdef _SYS_DXBREAK_ON_ERRORS
		 __asm int 3
#endif
	}
	return hr;
}
#define SYS_DXTRACE(hr) __SYS_DXTRACE(__FILE__, __LINE__, hr)
#else
#define SYS_DXTRACE(hr) (hr)
#endif

struct DX_DisplayMode 
{
	int					lWidth;
	int					lHeight;
	int					BitsPerPixel;
	int					RefreshRate;
};



