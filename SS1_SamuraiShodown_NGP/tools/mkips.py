import sys
def make(orig, new):
    out=bytearray(b'PATCH'); i=0; n=len(new)
    while i<n:
        if i<len(orig) and new[i]==orig[i]: i+=1; continue
        j=i; same=0
        while j<n and same<6:
            if j<len(orig) and new[j]==orig[j]: same+=1
            else: same=0
            j+=1
        end=j-same if same>=6 else j
        chunk=new[i:end]
        k=0
        while k<len(chunk):
            ln=min(0xFFFF,len(chunk)-k); off=i+k
            if off==0x454F46: off-=1; ln+=1; k-=1   # 'EOF' 회피
            out+=off.to_bytes(3,'big')+ln.to_bytes(2,'big')+chunk[k:k+ln]
            k+=ln
        i=end
    return bytes(out+b'EOF')
if __name__=='__main__':
    o=open(sys.argv[1],'rb').read(); n=open(sys.argv[2],'rb').read()
    p=make(o,n); open(sys.argv[3],'wb').write(p); print(sys.argv[3], len(p),'B')
