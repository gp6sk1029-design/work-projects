// Sysmac同梱の変換処理でラダー各行を読み取る。実機やアプリの状態は変更しない。
using System;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Text;
using System.Reflection.Emit;
using System.Collections.Generic;
public static class NativeLadderCheck {
 public static string LoadSection(string source,string suffix) {
  var assembly=Assembly.LoadFrom(@"C:\Program Files (x86)\OMRON\Sysmac Studio\Modules\Nex\NexProgramming.dll");
  var type=assembly.GetType("Omron.Cxap.Modules.NexLadderDiagram.Implementation.Editor.Services.CompactLadderPersister");
  var loader=Activator.CreateInstance(type);
  using(var zip=ZipFile.OpenRead(source)) {
   foreach(var entry in zip.Entries) {
    if(!entry.FullName.EndsWith(suffix))continue;
    using(var stream=entry.Open()) {
     var args=new object[]{stream,null};var result=type.GetMethod("Load").Invoke(loader,args);
     var resultType=result.GetType();var ok=resultType.GetProperty("Succeeded").GetValue(result,null);
     var failed=resultType.GetProperty("FailedRungNumbers").GetValue(result,null) as System.Collections.IEnumerable;
     var text=new StringBuilder("SUCCEEDED="+ok+" FAILED_ROWS=");
     if(failed!=null)foreach(var row in failed)text.Append(row+",");
     if(args[1]!=null) {
      text.Append(" MODEL_TYPE="+args[1].GetType().FullName);
      foreach(var p in args[1].GetType().GetProperties()) if(p.Name=="Rungs") {
       var items=p.GetValue(args[1],null) as System.Collections.IEnumerable;int count=0;
       foreach(var item in items)count++;text.Append(" RUNG_COUNT="+count);
      }
     }
     return text.ToString();
    }
   }
  }
  return "NOT_FOUND";
 }
 public static string Inspect(string method) {
  var assembly=Assembly.LoadFrom(@"C:\Program Files (x86)\OMRON\Sysmac Studio\Modules\Nex\NexProgramming.dll");
  var type=assembly.GetType("NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToNormalRungConverter");
  var result=new StringBuilder();
  var methods=type.GetMethods(BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Instance|BindingFlags.Static|BindingFlags.DeclaredOnly);
  if(method=="") {foreach(var m in methods)result.AppendLine(m.ToString());return result.ToString();}
  var opcodes=new Dictionary<short,OpCode>();
  foreach(var f in typeof(OpCodes).GetFields(BindingFlags.Public|BindingFlags.Static)) if(f.FieldType==typeof(OpCode)) {var op=(OpCode)f.GetValue(null);opcodes[op.Value]=op;}
  foreach(var m in methods) {
   if(m.Name!=method) continue;
   result.AppendLine(m.ToString());var body=m.GetMethodBody();if(body==null)continue;
   foreach(var h in body.ExceptionHandlingClauses)result.AppendLine("HANDLER "+h.Flags+" "+h.TryOffset+".."+(h.TryOffset+h.TryLength)+" => "+h.HandlerOffset);
   var il=body.GetILAsByteArray();int p=0;
   while(p<il.Length) {
    int offset=p;short code=il[p++];if(code==0xfe)code=(short)(0xfe00|il[p++]);var op=opcodes[code];string value="";int token;
    switch(op.OperandType) {
     case OperandType.InlineNone:break;
     case OperandType.ShortInlineI:case OperandType.ShortInlineVar:value=il[p++].ToString();break;
     case OperandType.InlineVar:value=BitConverter.ToUInt16(il,p).ToString();p+=2;break;
     case OperandType.ShortInlineBrTarget:value=(p+1+(sbyte)il[p]).ToString("x4");p++;break;
     case OperandType.InlineBrTarget:value=(p+4+BitConverter.ToInt32(il,p)).ToString("x4");p+=4;break;
     case OperandType.InlineI:value=BitConverter.ToInt32(il,p).ToString();p+=4;break;
     case OperandType.InlineI8:case OperandType.InlineR:p+=8;break;
     case OperandType.ShortInlineR:p+=4;break;
     case OperandType.InlineSwitch:int count=BitConverter.ToInt32(il,p);p+=4;value="SWITCH "+count;p+=count*4;break;
     default:
      token=BitConverter.ToInt32(il,p);p+=4;
      try {value=op.OperandType==OperandType.InlineString?m.Module.ResolveString(token):m.Module.ResolveMember(token).ToString();}catch{value="TOKEN "+token;}
      break;
    }
    result.AppendLine(offset.ToString("x4")+" "+op.Name+" "+value);
   }
  }
  return result.ToString();
 }
 public static string Check(string source,string suffix) {
  var assembly=Assembly.LoadFrom(@"C:\Program Files (x86)\OMRON\Sysmac Studio\Modules\Nex\NexProgramming.dll");
  var strings=assembly.GetType("NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToStringConverter");
  var normal=assembly.GetType("NexProgramming.LadderDiagram.Implementation.CompactLadderConverter.CompactRungToNormalRungConverter");
  var converter=Activator.CreateInstance(strings);
  var parse=strings.GetMethod("TryConvertBack");var convert=normal.GetMethod("TryConvert");
  var result=new StringBuilder();int total=0,parseFails=0,normalFails=0;
  using(var zip=ZipFile.OpenRead(source)) {
   foreach(var entry in zip.Entries) {
    if(!entry.FullName.EndsWith(suffix)) continue;
    using(var reader=new StreamReader(entry.Open(),Encoding.UTF8,true)) {
     string line;
     while((line=reader.ReadLine())!=null) {
      if(String.IsNullOrWhiteSpace(line)) continue;
      int row=total++;
      try {
       var args=new object[]{line,null};bool ok=(bool)parse.Invoke(converter,args);
       if(!ok) {parseFails++;result.AppendLine("PARSE FAIL "+row);continue;}
       var normalConverter=Activator.CreateInstance(normal,new object[]{args[1]});
       var normalArgs=new object[]{null};ok=(bool)convert.Invoke(normalConverter,normalArgs);
       if(!ok){normalFails++;result.AppendLine("MODEL FAIL "+row);
        if(normalFails==1) {
         try {
          var diagnostic=Activator.CreateInstance(normal,new object[]{args[1]});
          normal.GetMethod("Convert",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(diagnostic,new object[]{null});
         } catch(Exception detail) {result.AppendLine(detail.ToString());}
        }
       }
      }catch(Exception ex){normalFails++;result.AppendLine("EXCEPTION "+row+" "+ex.ToString());}
     }
    }
   }
  }
  result.AppendLine("TOTAL="+total+" PARSE_FAIL="+parseFails+" MODEL_FAIL="+normalFails);
  return result.ToString();
 }
}
