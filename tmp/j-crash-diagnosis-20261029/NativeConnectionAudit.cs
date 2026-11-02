// 読込み成功だけでなく、コイルの入出力接続を実モデルで検査する。プロジェクトは変更しない。
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
public static class NativeConnectionAudit {
 static object Get(object obj,string name) {return obj.GetType().GetProperty(name).GetValue(obj,null);}
 public static string Check(string path) {
  var a=Assembly.LoadFrom(@"C:\Program Files (x86)\OMRON\Sysmac Studio\Modules\Nex\NexProgramming.dll");
  var parserType=a.GetType("NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToStringConverter");
  var converterType=a.GetType("NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToNormalRungConverter");
  var parser=Activator.CreateInstance(parserType);var text=new StringBuilder();
  int rungs=0,coils=0,bad=0,fail=0;
  using(var z=ZipFile.OpenRead(path)) foreach(var e in z.Entries) {
   if(!e.FullName.EndsWith(".xml"))continue;
   using(var reader=new StreamReader(e.Open(),Encoding.UTF8,true)) {
    string line;int row=0;
    while((line=reader.ReadLine())!=null) {
     if(String.IsNullOrWhiteSpace(line))continue;
     if(!line.StartsWith("{\"CLs\""))break;
     int current=row++;rungs++;
     try {
      var args=new object[]{line,null};
      if(!(bool)parserType.GetMethod("TryConvertBack").Invoke(parser,args)){fail++;continue;}
      var conv=Activator.CreateInstance(converterType,new object[]{args[1]});var output=new object[]{null};
      if(!(bool)converterType.GetMethod("TryConvert").Invoke(conv,output)){fail++;continue;}
      foreach(var node in (IEnumerable)Get(output[0],"DiagramNodes")) {
       if(node.GetType().Name!="Coil")continue;
       coils++;int inEdges=0,outEdges=0,inPoints=0,outPoints=0;
       foreach(var cp in (IEnumerable)Get(node,"ConnectionPoints")) {
        bool input=(bool)Get(cp,"IsInputConnection");int edgeCount=0;
        foreach(var edge in (IEnumerable)Get(cp,"Edges"))edgeCount++;
        if(input){inPoints++;inEdges+=edgeCount;}else{outPoints++;outEdges+=edgeCount;}
       }
       if(inEdges==0||outEdges==0) {
        bad++;text.AppendLine("MISSING_CONNECTION entry="+e.FullName+" row="+current+" variable="+Get(node,"Variable")+" inputPoints="+inPoints+" outputPoints="+outPoints+" inputEdges="+inEdges+" outputEdges="+outEdges);
       }
      }
     }catch(Exception ex){fail++;text.AppendLine("AUDIT_EXCEPTION entry="+e.FullName+" row="+current+" "+ex.GetBaseException().Message);}
    }
   }
  }
  text.AppendLine("TOTAL_RUNGS="+rungs+" COILS="+coils+" MISSING="+bad+" PARSE_MODEL_FAIL="+fail);
  return text.ToString();
 }
}
