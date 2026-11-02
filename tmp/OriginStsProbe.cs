// 埋込DBは必ずメモリコピーで開き、原本を変更しない。
using System;
using System.IO;
using System.IO.Compression;
using System.Text;
using System.Collections.Generic;
using STSdb4.Database;
public static class OriginStsProbe {
 public static string Describe(string source) {
  var result = new StringBuilder();
  using (var zip = ZipFile.OpenRead(source)) {
   foreach(var entry in zip.Entries) {
    if (!entry.FullName.EndsWith("SysmacStudio.stsdb4")) continue;
    using (var stream = new MemoryStream()) {
     using (var input = entry.Open()) input.CopyTo(stream);
     stream.Position=0;
     using (var db=STSdb.FromStream(stream)) {
      foreach (var descriptor in db) {
       if (descriptor.RecordType != typeof(List<string>)) continue;
       var table=db.OpenXTable<string,List<string>>(descriptor.Name);
       int count=0, total=0;
       foreach (var row in table) {
        total++;
        bool hit=row.Key.Contains("_Swv_") || row.Value.Exists(s=>s.Contains("_Swv_"));
        if (!hit) continue;
        count++;
        if(count<=3) result.AppendLine(descriptor.Name+" KEY="+row.Key+" VALUE="+String.Join(" || ",row.Value));
       }
       result.AppendLine(descriptor.Name+" TOTAL="+total+" MATCH COUNT="+count);
      }
     }
    }
   }
  }
  return result.ToString();
 }
}
