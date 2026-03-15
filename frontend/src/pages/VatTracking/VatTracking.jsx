import React, { useState, useEffect } from 'react';
import api from '../../api';
import './VatTracking.css';
import * as xlsx from 'xlsx';

const VatTracking = () => {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filters, setFilters] = useState({
    start_date: '',
    end_date: '',
    vat_company: 'all',
    q: ''
  });

  const [uploadLoading, setUploadLoading] = useState(false);
  const [message, setMessage] = useState({ type: '', text: '' });

  const fetchReport = async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filters.start_date) params.append('start_date', filters.start_date);
      if (filters.end_date) params.append('end_date', filters.end_date);
      if (filters.vat_company !== 'all') params.append('vat_company', filters.vat_company);
      if (filters.q) params.append('q', filters.q);

      const response = await api.get(`/api/vat/report/?${params.toString()}`);
      setData(response.data);
      setMessage({ type: '', text: '' });
    } catch (err) {
      setMessage({ type: 'error', text: 'Failed to fetch report data.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReport();
  }, [filters]);

  const handleFilterChange = (e) => {
    const { name, value } = e.target;
    setFilters(prev => ({ ...prev, [name]: value }));
  };

  const handleFileUpload = async (event, type) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploadLoading(true);
    setMessage({ type: 'info', text: `Uploading ${type} data...` });

    const formData = new FormData();
    formData.append('file', file);
    formData.append('type', type);

    try {
      const res = await api.post('/api/vat/import/', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      setMessage({ type: 'success', text: `Successfully imported ${res.data.processed} records.` });
      fetchReport(); // Refresh data
    } catch (err) {
      setMessage({ type: 'error', text: `Error importing file: ${err.response?.data?.error || err.message}` });
    } finally {
      setUploadLoading(false);
      event.target.value = null; // reset input
    }
  };

  const handleInlineEdit = async (itemType, id, field, value) => {
    try {
      await api.put('/api/vat/report/', {
        item_type: itemType,
        id: id,
        [field]: value
      });
      // Update local state without fetching to keep it snappy
      setData(prevData => prevData.map(item => {
        if (itemType === 'buy' && item.id === id) {
          return { ...item, [field]: value };
        } else if (itemType === 'sale' && item.sale_match?.id === id) {
          return { ...item, sale_match: { ...item.sale_match, [field]: value } };
        }
        return item;
      }));
    } catch (err) {
      alert('Failed to update value.');
    }
  };

  const exportToExcel = () => {
    if (data.length === 0) return;

    const exportData = data.map(item => ({
      'Serial No': item.serial_no,
      'วันที่ซื้อ': item.date || '',
      'เลขที่เอกสารซื้อ': item.document_no || '',
      'ชื่อผู้จำหน่าย': item.supplier_name || '',
      'สินค้า': item.product_name,
      'ราคาซื้อ': item.purchase_price,
      'บริษัท VAT': item.vat_company || '',
      'วิธีชำระ (เข้า)': item.payment_method_in || '',
      'ธนาคาร (เข้า)': item.bank_in || '',
      
      'วันที่ขาย': item.sale_match?.date || '',
      'เลขที่เอกสารขาย': item.sale_match?.document_no || '',
      'ชื่อลูกค้า': item.sale_match?.customer_name || '',
      'ราคาขาย': item.sale_match?.sale_price || '',
      'วิธีชำระ (ออก)': item.sale_match?.payment_method_out || '',
      'บริษัท (ออก)': item.sale_match?.company_out || ''
    }));

    const worksheet = xlsx.utils.json_to_sheet(exportData);
    const workbook = xlsx.utils.book_new();
    xlsx.utils.book_append_sheet(workbook, worksheet, "VAT_Report");
    xlsx.writeFile(workbook, `VAT_Report_${new Date().toISOString().slice(0,10)}.xlsx`);
  };

  return (
    <div className="vat-container">
      <header className="vat-header">
        <div>
          <h1 className="vat-title">ระบบจัดการ VAT คงเหลือ</h1>
          <p className="vat-subtitle">VAT Orders Tracking & Reconciliation</p>
        </div>
        <div className="vat-actions">
          <label className="btn btn-outline btn-upload">
            <input type="file" accept=".xls,.xlsx" onChange={(e) => handleFileUpload(e, 'buy')} disabled={uploadLoading} hidden />
            <span className="icon">📥</span> นำเข้าข้อมูล ซื้อ
          </label>
          <label className="btn btn-outline btn-upload">
            <input type="file" accept=".xls,.xlsx" onChange={(e) => handleFileUpload(e, 'sale')} disabled={uploadLoading} hidden />
            <span className="icon">📤</span> นำเข้าข้อมูล ขาย
          </label>
          <button className="btn btn-primary" onClick={exportToExcel} disabled={data.length === 0}>
            <span className="icon">📊</span> Export Excel
          </button>
        </div>
      </header>

      {message.text && (
        <div className={`alert alert-${message.type}`}>
          {message.text}
        </div>
      )}

      <div className="vat-filters">
        <div className="filter-group">
          <label>ค้นหาสินค้า (Serial/ชื่อ)</label>
          <input type="text" name="q" value={filters.q} onChange={handleFilterChange} placeholder="Enter keywords..." className="form-input" />
        </div>
        <div className="filter-group">
          <label>บริษัท VAT</label>
          <select name="vat_company" value={filters.vat_company} onChange={handleFilterChange} className="form-select">
            <option value="all">ทั้งหมด (All)</option>
            <option value="NONE">- ไม่มี VAT -</option>
            <option value="NMK">NMK</option>
            {/* Add more dynamically or statically as needed */}
          </select>
        </div>
        <div className="filter-group">
          <label>ตั้งแต่วันที่ (ซื้อ)</label>
          <input type="date" name="start_date" value={filters.start_date} onChange={handleFilterChange} className="form-input" />
        </div>
        <div className="filter-group">
          <label>ถึงวันที่ (ซื้อ)</label>
          <input type="date" name="end_date" value={filters.end_date} onChange={handleFilterChange} className="form-input" />
        </div>
      </div>

      <div className="vat-table-wrapper">
        <div className="table-responsive">
          <table className="vat-table">
            <thead>
              <tr>
                <th colSpan="8" className="th-buy">ฝั่งซื้อ (Buy In)</th>
                <th colSpan="5" className="th-sale">ฝั่งขาย (Sale Out)</th>
              </tr>
              <tr>
                <th>Serial / Item</th>
                <th>วันที่ซื้อ</th>
                <th>Doc No.</th>
                <th>ราคาซื้อ</th>
                <th>ผู้จำหน่าย</th>
                <th>บริษัท VAT</th>
                <th>ชำระ (เข้า)</th>
                <th>ธนาคาร</th>
                
                <th>วันที่ขาย</th>
                <th>Doc No.</th>
                <th>ลูกค้า</th>
                <th>ราคาขาย</th>
                <th>ชำระ (ออก)</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="13" className="loading-cell">Loading data...</td></tr>
              ) : data.length === 0 ? (
                <tr><td colSpan="13" className="empty-cell">No records found.</td></tr>
              ) : (
                data.map((item, idx) => (
                  <tr key={item.id} className={idx % 2 === 0 ? 'row-even' : 'row-odd'}>
                    <td className="cell-bold">
                      <div className="serial-no">{item.serial_no}</div>
                      <div className="product-name" title={item.product_name}>{item.product_name}</div>
                    </td>
                    <td>{item.date}</td>
                    <td className="cell-muted">{item.document_no}</td>
                    <td className="cell-money">{item.purchase_price ? Number(item.purchase_price).toLocaleString() : ''}</td>
                    <td>{item.supplier_name}</td>
                    
                    {/* Inline Edit for Buy */}
                    <td>
                      <input 
                        className="inline-input" 
                        value={item.vat_company || ''} 
                        onChange={(e) => handleInlineEdit('buy', item.id, 'vat_company', e.target.value)}
                        placeholder="VAT Co."
                      />
                    </td>
                    <td>
                      <input 
                        className="inline-input" 
                        value={item.payment_method_in || ''} 
                        onChange={(e) => handleInlineEdit('buy', item.id, 'payment_method_in', e.target.value)}
                        placeholder="Method"
                      />
                    </td>
                    <td>
                      <input 
                        className="inline-input" 
                        value={item.bank_in || ''} 
                        onChange={(e) => handleInlineEdit('buy', item.id, 'bank_in', e.target.value)}
                        placeholder="Bank"
                      />
                    </td>

                    {/* Sale Match Side */}
                    {item.sale_match ? (
                      <>
                        <td className="sale-cell">{item.sale_match.date}</td>
                        <td className="sale-cell cell-muted">{item.sale_match.document_no}</td>
                        <td className="sale-cell">{item.sale_match.customer_name}</td>
                        <td className="sale-cell cell-money">{item.sale_match.sale_price ? Number(item.sale_match.sale_price).toLocaleString() : ''}</td>
                        <td className="sale-cell">
                          <input 
                            className="inline-input" 
                            value={item.sale_match.payment_method_out || ''} 
                            onChange={(e) => handleInlineEdit('sale', item.sale_match.id, 'payment_method_out', e.target.value)}
                            placeholder="Method Out"
                          />
                        </td>
                      </>
                    ) : (
                      <td colSpan="5" className="unmatched-cell">
                        <span className="badge badge-warning">ยังไม่ได้ขาย</span>
                      </td>
                    )}
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default VatTracking;
