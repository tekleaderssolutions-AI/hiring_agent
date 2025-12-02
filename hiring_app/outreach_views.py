@csrf_exempt
def get_outreach_logs(request):
    """Get all candidate outreach logs with email status"""
    from db import get_connection
    
    conn = get_connection()
    try:
        cur = conn.cursor()
        
        cur.execute("""
            SELECT 
                co.id,
                co.candidate_name,
                co.candidate_email,
                co.ats_score,
                co.acknowledgement,
                co.sent_at,
                co.acknowledged_at,
                m.title as jd_title
            FROM candidate_outreach co
            LEFT JOIN memories m ON co.jd_id = m.id
            ORDER BY co.sent_at DESC
            LIMIT 100
        """)
        
        rows = cur.fetchall()
        cur.close()
        
        logs = []
        for row in rows:
            logs.append({
                "id": str(row[0]),
                "candidate_name": row[1],
                "candidate_email": row[2],
                "ats_score": row[3],
                "acknowledgement": row[4] if row[4] else "pending",
                "sent_at": str(row[5]) if row[5] else None,
                "acknowledged_at": str(row[6]) if row[6] else None,
                "jd_title": row[7]
            })
        
        return JsonResponse({
            "total": len(logs),
            "logs": logs
        })
        
    except Exception as e:
        return JsonResponse({'error': f"Error fetching outreach logs: {str(e)}"}, status=500)
    finally:
        conn.close()
