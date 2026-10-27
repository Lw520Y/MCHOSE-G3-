$ErrorActionPreference = 'Stop'
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
using System.Text;

public static class HidProbe {
    [StructLayout(LayoutKind.Sequential)]
    public struct HIDD_ATTRIBUTES { public int Size; public ushort VendorID; public ushort ProductID; public ushort VersionNumber; }

    [StructLayout(LayoutKind.Sequential)]
    public struct HIDP_CAPS {
        public ushort Usage;
        public ushort UsagePage;
        public ushort InputReportByteLength;
        public ushort OutputReportByteLength;
        public ushort FeatureReportByteLength;
        [MarshalAs(UnmanagedType.ByValArray, SizeConst = 17)] public ushort[] Reserved;
        public ushort NumberLinkCollectionNodes;
        public ushort NumberInputButtonCaps;
        public ushort NumberInputValueCaps;
        public ushort NumberInputDataIndices;
        public ushort NumberOutputButtonCaps;
        public ushort NumberOutputValueCaps;
        public ushort NumberOutputDataIndices;
        public ushort NumberFeatureButtonCaps;
        public ushort NumberFeatureValueCaps;
        public ushort NumberFeatureDataIndices;
    }

    [DllImport("hid.dll", SetLastError = true)]
    public static extern bool HidD_GetAttributes(IntPtr h, ref HIDD_ATTRIBUTES a);
    [DllImport("hid.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool HidD_GetProductString(IntPtr h, StringBuilder b, int len);
    [DllImport("hid.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool HidD_GetManufacturerString(IntPtr h, StringBuilder b, int len);
    [DllImport("hid.dll", SetLastError = true)]
    public static extern bool HidD_GetPreparsedData(IntPtr h, out IntPtr p);
    [DllImport("hid.dll", SetLastError = true)]
    public static extern bool HidD_FreePreparsedData(IntPtr p);
    [DllImport("hid.dll", SetLastError = true)]
    public static extern int HidP_GetCaps(IntPtr p, ref HIDP_CAPS c);
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern IntPtr CreateFile(string path, uint access, uint share, IntPtr sa, uint disp, uint flags, IntPtr tmpl);
    [DllImport("kernel32.dll", SetLastError = true)]
    public static extern bool CloseHandle(IntPtr h);
}
"@

$base = 'HKLM:\SYSTEM\CurrentControlSet\Control\DeviceClasses\{4d1e55b2-f16f-11cf-88cb-001111000030}'
Get-ChildItem $base | ForEach-Object {
    $raw = $_.PSChildName
    if ($raw -notmatch 'VID_258A') { return }
    $iface = $raw -replace '^##\?#', '\\?\'
    $h = [HidProbe]::CreateFile($iface, 0, 3, [IntPtr]::Zero, 3, 0, [IntPtr]::Zero)
    if ($h.ToInt64() -eq -1 -or $h -eq [IntPtr]::Zero) {
        Write-Output "OPEN FAIL $iface"
        return
    }
    try {
        $attr = New-Object HidProbe+HIDD_ATTRIBUTES
        $attr.Size = [Runtime.InteropServices.Marshal]::SizeOf($attr)
        [void][HidProbe]::HidD_GetAttributes($h, [ref]$attr)
        $prod = New-Object System.Text.StringBuilder 256
        [void][HidProbe]::HidD_GetProductString($h, $prod, 512)
        $man = New-Object System.Text.StringBuilder 256
        [void][HidProbe]::HidD_GetManufacturerString($h, $man, 512)
        $pp = [IntPtr]::Zero
        $caps = New-Object HidProbe+HIDP_CAPS
        $ok = [HidProbe]::HidD_GetPreparsedData($h, [ref]$pp)
        if ($ok) {
            [void][HidProbe]::HidP_GetCaps($pp, [ref]$caps)
            [void][HidProbe]::HidD_FreePreparsedData($pp)
        }
        Write-Output ("{0}`n  VID={1:X4} PID={2:X4} VER={3:X4} MAN='{4}' PROD='{5}'`n  usage={6:X4}:{7:X4} IN={8} OUT={9} FEAT={10}" -f `
            $iface, $attr.VendorID, $attr.ProductID, $attr.VersionNumber, $man.ToString(), $prod.ToString(), `
            $caps.UsagePage, $caps.Usage, $caps.InputReportByteLength, $caps.OutputReportByteLength, $caps.FeatureReportByteLength)
    }
    finally {
        [void][HidProbe]::CloseHandle($h)
    }
}
