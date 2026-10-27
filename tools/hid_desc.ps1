$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class HidDesc {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr CreateFile(string path, uint access, uint share, IntPtr sa, uint disp, uint flags, IntPtr tmpl);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool DeviceIoControl(IntPtr h, uint code, IntPtr inBuf, uint inSize, IntPtr outBuf, uint outSize, out uint bytes, IntPtr overlapped);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool CloseHandle(IntPtr h);

    public static string Get(string path) {
        IntPtr h = CreateFile(path, 0, 3, IntPtr.Zero, 3, 0, IntPtr.Zero);
        if (h.ToInt64() == -1) return "OPEN FAIL err=" + Marshal.GetLastWin32Error();
        IntPtr buf = Marshal.AllocHGlobal(8192);
        try {
            uint got;
            bool ok = DeviceIoControl(h, 0x000B0000, IntPtr.Zero, 0, buf, 8192, out got, IntPtr.Zero);
            if (!ok) return "IOCTL FAIL err=" + Marshal.GetLastWin32Error();
            byte[] data = new byte[got];
            Marshal.Copy(buf, data, 0, (int)got);
            return BitConverter.ToString(data).Replace("-", " ");
        }
        finally {
            Marshal.FreeHGlobal(buf);
            CloseHandle(h);
        }
    }
}
"@

$paths = @{
    'FF00-8'  = '\\?\HID#VID_258A&PID_0138&MI_01&Col04#7&1cd81421&0&0003#{4d1e55b2-f16f-11cf-88cb-001111000030}'
    'FF00-1K' = '\\?\HID#VID_258A&PID_0138&MI_01&Col05#7&1cd81421&0&0004#{4d1e55b2-f16f-11cf-88cb-001111000030}'
    'FF01'    = '\\?\HID#VID_258A&PID_0138&MI_01&Col06#7&1cd81421&0&0005#{4d1e55b2-f16f-11cf-88cb-001111000030}'
    'FF02'    = '\\?\HID#VID_258A&PID_0138&MI_01&Col07#7&1cd81421&0&0006#{4d1e55b2-f16f-11cf-88cb-001111000030}'
}
foreach ($k in $paths.Keys) {
    Write-Output "=== $k"
    Write-Output ([HidDesc]::Get($paths[$k]))
}
